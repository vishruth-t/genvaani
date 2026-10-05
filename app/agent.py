import asyncio
import json
import structlog
from app.sarvam.llm import stream_chat_completion
from app.sarvam.tts import TTSClient
from app.tools import TOOLS_SCHEMA, execute_tool
from app.knowledge import rag_db

logger = structlog.get_logger(__name__)

class VoiceAgent:
    def __init__(self, twilio_ws, stream_sid):
        self.twilio_ws = twilio_ws
        self.stream_sid = stream_sid
        self.tts_client = None
        self.chat_history = [
            {"role": "system", "content": "You are a helpful phone assistant for a company. Keep responses brief, conversational, and natural. Do not use markdown. If asked about appointments or orders, use your tools."}
        ]
        self._llm_task = None
        self.state = "LISTENING" # LISTENING, THINKING, SPEAKING
        self._silence_task = None
        
    def reset_silence_timer(self, timeout=8.0):
        if self._silence_task:
            self._silence_task.cancel()
        self._silence_task = asyncio.create_task(self._silence_handler(timeout))
        
    async def reset_silence_timer_async(self, timeout=8.0):
        self.reset_silence_timer(timeout)
        
    async def _silence_handler(self, timeout):
        try:
            await asyncio.sleep(timeout)
            if self.state == "LISTENING":
                logger.info("Silence timeout triggered")
                # Trigger a gentle prompt
                await self._process_llm_and_tts("hi-IN", custom_prompt="User has been silent for a while. Ask them if they are still there in a few words.")
        except asyncio.CancelledError:
            pass
        
    async def handle_user_transcript(self, text: str, language_code: str):
        """Called when a final transcript is received from STT."""
        self.reset_silence_timer()
        
        if not text.strip():
            return
            
        logger.info("User said", text=text, lang=language_code)
        
        # Simple RAG injection
        rag_context = rag_db.search(text)
        if rag_context:
            self.chat_history.append({"role": "system", "content": f"Context: {rag_context}"})
            
        self.chat_history.append({"role": "user", "content": text})
        
        self.state = "THINKING"
        
        # Stop any ongoing TTS just in case
        if self.tts_client:
            await self.tts_client.stop()
            
        # Start a new LLM task
        if self._llm_task:
            self._llm_task.cancel()
            
        self._llm_task = asyncio.create_task(self._process_llm_and_tts(language_code))

    async def _process_llm_and_tts(self, language_code: str, custom_prompt: str = None):
        try:
            # Map auto-detected STT language to TTS language/speaker
            tts_lang = "hi-IN" # fallback
            speaker = "meera"  # fallback
            
            if language_code == "hi-IN":
                tts_lang = "hi-IN"
            elif language_code == "en-IN":
                tts_lang = "en-IN"
            elif language_code == "or-IN":
                tts_lang = "od-IN" # Handle STT (or-IN) vs TTS (od-IN)
            
            # Start fresh TTS client for this turn
            self.tts_client = TTSClient(self.twilio_ws, self.stream_sid, speaker=speaker, language_code=tts_lang)
            await self.tts_client.start()
            
            self.state = "SPEAKING"
            
            agent_reply = ""
            sentence_buffer = ""
            
            messages_to_send = self.chat_history.copy()
            if custom_prompt:
                messages_to_send.append({"role": "system", "content": custom_prompt})
            
            tool_calls_received = []
            
            # Stream from LLM
            async for item in stream_chat_completion(messages_to_send, tools=TOOLS_SCHEMA):
                if item["type"] == "text":
                    token = item["content"]
                    agent_reply += token
                    sentence_buffer += token
                    
                    # Check for sentence boundaries to chunk TTS
                    if any(punc in sentence_buffer for punc in ['.', '?', '!', '।', '॥', '\n']):
                        if sentence_buffer.strip():
                            await self.tts_client.send_text(sentence_buffer.strip())
                            sentence_buffer = ""
                elif item["type"] == "tool_call":
                    tool_calls_received.append(item["tool_call"])
                    
            # Flush any remaining text
            if sentence_buffer.strip():
                await self.tts_client.send_text(sentence_buffer.strip())
                
            await self.tts_client.flush()
            
            if agent_reply:
                self.chat_history.append({"role": "assistant", "content": agent_reply})
                logger.info("Agent said", text=agent_reply)
                
            if tool_calls_received:
                self.chat_history.append({"role": "assistant", "tool_calls": tool_calls_received, "content": None})
                for tc in tool_calls_received:
                    name = tc["function"]["name"]
                    args = {}
                    try:
                        args = json.loads(tc["function"]["arguments"])
                    except json.JSONDecodeError:
                        pass
                        
                    result = execute_tool(name, args)
                    self.chat_history.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "name": name,
                        "content": result
                    })
                    
                # Continue conversation after tool call
                self._llm_task = asyncio.create_task(self._process_llm_and_tts(language_code))
                return
            
            self.state = "LISTENING"
            
        except asyncio.CancelledError:
            logger.info("LLM/TTS processing cancelled (likely barge-in)")
        except Exception as e:
            logger.error(f"Error in LLM/TTS pipeline: {e}")
            self.state = "LISTENING"
            
    async def handle_barge_in(self):
        """Called when user starts speaking while agent is SPEAKING."""
        if self.state == "SPEAKING":
            logger.info("Barge-in detected!")
            
            # 1. Clear Twilio audio buffer
            clear_msg = {
                "event": "clear",
                "streamSid": self.stream_sid
            }
            await self.twilio_ws.send_text(json.dumps(clear_msg))
            
            # 2. Stop TTS and LLM
            if self.tts_client:
                await self.tts_client.stop()
                self.tts_client = None
                
            if self._llm_task:
                self._llm_task.cancel()
                self._llm_task = None
                
            self.state = "LISTENING"

    async def stop(self):
        if self.tts_client:
            await self.tts_client.stop()
        if self._llm_task:
            self._llm_task.cancel()
        if self._silence_task:
            self._silence_task.cancel()
