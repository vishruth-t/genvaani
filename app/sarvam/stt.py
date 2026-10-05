import asyncio
import json
import structlog
import websockets
from app.config import settings

logger = structlog.get_logger(__name__)

STT_WS_URL = "wss://api.sarvam.ai/speech-to-text-realtime/ws"

class STTClient:
    def __init__(self):
        self.audio_queue = asyncio.Queue()
        self.ws = None
        self._tasks = []
        self.on_final_transcript = None
        self.on_speech_start = None
        self.on_speech_end = None

    async def start(self):
        url = (f"{STT_WS_URL}?"
               f"language_code=auto&"
               f"stream_type=fast&"
               f"encoding=mulaw&"
               f"sample_rate=8000")
               
        headers = {
            "api-subscription-key": settings.sarvam_api_key
        }
        
        logger.info("Connecting to Sarvam STT...")
        try:
            self.ws = await websockets.connect(url, extra_headers=headers)
            logger.info("Connected to Sarvam STT")
            
            self._tasks.append(asyncio.create_task(self._receive_loop()))
            self._tasks.append(asyncio.create_task(self._send_loop()))
        except Exception as e:
            logger.exception(f"Failed to connect to STT: {e}")

    async def stop(self):
        if self.ws:
            try:
                await self.ws.send(json.dumps({"event": "end"}))
                await self.ws.close()
            except websockets.exceptions.ConnectionClosed:
                pass
        for t in self._tasks:
            t.cancel()

    def add_audio(self, base64_payload: str):
        self.audio_queue.put_nowait(base64_payload)

    async def _send_loop(self):
        try:
            while True:
                payload = await self.audio_queue.get()
                msg = {
                    "event": "audio_input",
                    "audio": payload
                }
                await self.ws.send(json.dumps(msg))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in STT send loop: {e}")

    async def _receive_loop(self):
        try:
            async for message in self.ws:
                data = json.loads(message)
                event = data.get("event")
                
                if event == "transcript.partial":
                    logger.info("STT Partial", text=data.get("text"), lang=data.get("language"))
                elif event == "transcript.final":
                    logger.info("STT Final", text=data.get("text"), lang=data.get("language"))
                    if self.on_final_transcript:
                        asyncio.create_task(self.on_final_transcript(data.get("text"), data.get("language")))
                elif event == "vad.speech_start":
                    logger.info("VAD Speech Start")
                    if self.on_speech_start:
                        asyncio.create_task(self.on_speech_start())
                elif event == "vad.speech_end":
                    logger.info("VAD Speech End")
                    if self.on_speech_end:
                        asyncio.create_task(self.on_speech_end())
                elif event == "error":
                    logger.error("STT Error", error=data)
                else:
                    logger.debug("STT Event", event=event, data=data)
        except asyncio.CancelledError:
            pass
        except websockets.exceptions.ConnectionClosed:
            logger.info("STT connection closed")
        except Exception as e:
            logger.error(f"Error in STT receive loop: {e}")
