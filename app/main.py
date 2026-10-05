from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, Response
import uvicorn
import structlog
from app.config import settings
from app.logging_config import setup_logging
from app.twilio_handler import twilio_media_stream_handler

setup_logging()
logger = structlog.get_logger(__name__)

app = FastAPI(title="Sarvam Voice Agent")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.api_route("/voice", methods=["GET", "POST"])
async def voice(request: Request):
    """
    Twilio Webhook for incoming calls. Returns TwiML.
    """
    host = request.headers.get("host", "")
    if settings.public_url:
        # Strip https:// for wss
        domain = settings.public_url.replace("https://", "").replace("http://", "")
        ws_url = f"wss://{domain}/media"
    else:
        ws_url = f"wss://{host}/media"
        
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{ws_url}" />
    </Connect>
</Response>
"""
    return Response(content=twiml, media_type="text/xml")

@app.websocket("/media")
async def media_stream(websocket: WebSocket):
    """
    WebSocket endpoint for Twilio Media Streams.
    """
    await websocket.accept()
    logger.info("Twilio media stream connected")
    try:
        await twilio_media_stream_handler(websocket)
    except WebSocketDisconnect:
        logger.info("Twilio media stream disconnected")
    except Exception as e:
        logger.exception(f"Error in media stream: {e}")
    finally:
        # Ensure we close if not already closed
        try:
            await websocket.close()
        except:
            pass

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
