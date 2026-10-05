import json
import structlog
from fastapi import WebSocket
from app.sarvam.stt import STTClient
from app.agent import VoiceAgent

logger = structlog.get_logger(__name__)

async def twilio_media_stream_handler(websocket: WebSocket):
    """
    Handles Twilio Media Streams protocol.
    For Milestone 3, we orchestrate STT -> LLM -> TTS.
    """
    stream_sid = None
    stt_client = None
    agent = None
    
    try:
        async for message in websocket.iter_text():
            data = json.loads(message)
            event = data.get("event")
            
            if event == "connected":
                logger.info("Received connected event", data=data)
                
            elif event == "start":
                stream_sid = data["start"]["streamSid"]
                logger.info("Received start event", stream_sid=stream_sid)
                
                # Initialize Agent
                agent = VoiceAgent(websocket, stream_sid)
                
                # Initialize STT client and hook up callbacks
                stt_client = STTClient()
                
                # We need to monkey patch or modify STTClient to call agent on transcript
                # But since STTClient is in another file, let's inject a callback
                stt_client.on_final_transcript = agent.handle_user_transcript
                stt_client.on_speech_start = agent.handle_barge_in
                stt_client.on_speech_end = agent.reset_silence_timer_async
                
                await stt_client.start()
                
            elif event == "media":
                payload = data["media"]["payload"]
                
                if stt_client:
                    stt_client.add_audio(payload)
                
            elif event == "stop":
                logger.info("Received stop event", stream_sid=stream_sid)
                break
                
            elif event == "mark":
                logger.info("Received mark event", stream_sid=stream_sid, data=data)
    finally:
        if stt_client:
            await stt_client.stop()
        if agent:
            await agent.stop()
