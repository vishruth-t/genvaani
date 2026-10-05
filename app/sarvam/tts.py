import asyncio
import json
import structlog
import websockets
from app.config import settings

logger = structlog.get_logger(__name__)

TTS_WS_URL = "wss://api.sarvam.ai/text-to-speech/ws"

class TTSClient:
    def __init__(self, twilio_ws, stream_sid, speaker="shubh", language_code="hi-IN"):
        self.twilio_ws = twilio_ws
        self.stream_sid = stream_sid
        self.speaker = speaker
        self.language_code = language_code
        self.ws = None
        self._recv_task = None

    async def start(self):
        headers = {
            "api-subscription-key": settings.sarvam_api_key
        }
        
        logger.info("Connecting to Sarvam TTS...")
        try:
            self.ws = await websockets.connect(f"{TTS_WS_URL}?model=bulbul:v3", extra_headers=headers)
            logger.info("Connected to Sarvam TTS")
            
            # Send config
            config_msg = {
                "type": "config",
                "data": {
                    "speaker": self.speaker,
                    "language_code": self.language_code,
                    "output_audio_codec": "mulaw",
                    "sample_rate": 8000,
                    "pace": 1.0,
                    "send_completion_event": True
                }
            }
            await self.ws.send(json.dumps(config_msg))
            
            self._recv_task = asyncio.create_task(self._receive_loop())
        except Exception as e:
            logger.exception(f"Failed to connect to TTS: {e}")

    async def stop(self):
        if self.ws:
            try:
                await self.ws.close()
            except websockets.exceptions.ConnectionClosed:
                pass
        if self._recv_task:
            self._recv_task.cancel()

    async def send_text(self, text: str):
        if not self.ws:
            return
        
        msg = {
            "type": "text",
            "data": {
                "text": text
            }
        }
        await self.ws.send(json.dumps(msg))

    async def flush(self):
        if not self.ws:
            return
        msg = {
            "type": "flush",
            "data": {}
        }
        await self.ws.send(json.dumps(msg))

    async def _receive_loop(self):
        try:
            async for message in self.ws:
                data = json.loads(message)
                msg_type = data.get("type")
                
                if msg_type == "audio":
                    payload = data.get("data", {}).get("audio")
                    if payload:
                        # Send base64 payload to Twilio
                        # Wait, Twilio expects 20ms chunks (160 bytes for mulaw).
                        # Sarvam TTS might send larger chunks.
                        # For now, we will send exactly what we receive, 
                        # but in production, we should frame it to 160 bytes.
                        # Since Twilio accepts larger chunks (they will buffer it internally up to some limit),
                        # we can try sending it directly. But it's best to chunk.
                        
                        outbound_msg = {
                            "event": "media",
                            "streamSid": self.stream_sid,
                            "media": {
                                "payload": payload
                            }
                        }
                        await self.twilio_ws.send_text(json.dumps(outbound_msg))
                        
                elif msg_type == "event":
                    event_type = data.get("data", {}).get("event_type")
                    if event_type == "final":
                        logger.info("TTS completed generation")
                        
                else:
                    logger.debug("TTS message", data=data)
        except asyncio.CancelledError:
            pass
        except websockets.exceptions.ConnectionClosed:
            logger.info("TTS connection closed")
        except Exception as e:
            logger.error(f"Error in TTS receive loop: {e}")
