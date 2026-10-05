import asyncio
import json
import base64
import sys
import argparse
import wave
import time
import websockets

async def simulate_call(ws_url: str, wav_file: str):
    print(f"Connecting to {ws_url}...")
    try:
        async with websockets.connect(ws_url) as ws:
            print("Connected! Sending 'connected' and 'start' events...")
            
            await ws.send(json.dumps({
                "event": "connected",
                "protocol": "Call",
                "version": "1.0.0"
            }))
            
            stream_sid = "MZfake_stream_sid"
            await ws.send(json.dumps({
                "event": "start",
                "sequenceNumber": "1",
                "start": {
                    "accountSid": "ACfake_account_sid",
                    "streamSid": stream_sid,
                    "callSid": "CAfake_call_sid",
                    "tracks": ["inbound"],
                    "mediaFormat": {
                        "encoding": "audio/x-mulaw",
                        "sampleRate": 8000,
                        "channels": 1
                    }
                },
                "streamSid": stream_sid
            }))
            
            # Start a task to read responses from the server
            async def receive_responses():
                try:
                    async for message in ws:
                        data = json.loads(message)
                        if data.get("event") == "media":
                            # It's echoing audio back or sending generated TTS
                            print(".", end="", flush=True)
                        else:
                            print(f"\nReceived: {data}")
                except Exception as e:
                    print(f"\nReceive loop ended: {e}")
            
            recv_task = asyncio.create_task(receive_responses())
            
            # Read and stream the WAV file
            # Assuming it's 8000Hz mono mulaw
            try:
                with open(wav_file, 'rb') as f:
                    print(f"Streaming {wav_file} (raw 8kHz mulaw)...")
                    seq = 2
                    
                    while True:
                        frames = f.read(160)
                        if not frames:
                            break
                        
                        payload = base64.b64encode(frames).decode('utf-8')
                        await ws.send(json.dumps({
                            "event": "media",
                            "sequenceNumber": str(seq),
                            "media": {
                                "track": "inbound",
                                "chunk": str(seq),
                                "timestamp": str(seq * 20),
                                "payload": payload
                            },
                            "streamSid": stream_sid
                        }))
                        seq += 1
                        
                        await asyncio.sleep(0.02)
                        
            except FileNotFoundError:
                print(f"File not found: {wav_file}")
                
            print("\nFinished sending audio. Waiting for a few seconds...")
            await asyncio.sleep(2)
            
            print("Sending 'stop' event...")
            await ws.send(json.dumps({
                "event": "stop",
                "sequenceNumber": str(seq),
                "streamSid": stream_sid,
                "stop": {
                    "accountSid": "ACfake_account_sid",
                    "callSid": "CAfake_call_sid"
                }
            }))
            
            recv_task.cancel()
            
    except Exception as e:
        print(f"Failed to connect or error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate Twilio Media Streams")
    parser.add_argument("--url", default="ws://localhost:8000/media", help="WebSocket URL")
    parser.add_argument("--wav", default="test_audio.wav", help="Path to WAV file (should be 8kHz mulaw)")
    args = parser.parse_args()
    
    asyncio.run(simulate_call(args.url, args.wav))
