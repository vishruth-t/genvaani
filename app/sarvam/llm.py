import json
import httpx
import structlog
from app.config import settings
from typing import AsyncGenerator

logger = structlog.get_logger(__name__)

LLM_URL = "https://api.sarvam.ai/v1/chat/completions"

async def stream_chat_completion(messages: list, tools: list = None, model: str = "sarvam-105b-conversations") -> AsyncGenerator[dict, None]:
    headers = {
        "api-subscription-key": settings.sarvam_api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "stream": True
    }
    
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    
    logger.info("Calling Sarvam LLM", model=model, has_tools=bool(tools))
    
    current_tool_calls = {}
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("POST", LLM_URL, json=payload, headers=headers) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0].get("delta", {})
                            
                            # Handle text content
                            if "content" in delta and delta["content"]:
                                yield {"type": "text", "content": delta["content"]}
                                
                            # Handle tool calls
                            if "tool_calls" in delta and delta["tool_calls"]:
                                for tc in delta["tool_calls"]:
                                    idx = tc["index"]
                                    if idx not in current_tool_calls:
                                        current_tool_calls[idx] = {
                                            "id": tc.get("id"),
                                            "type": "function",
                                            "function": {
                                                "name": tc.get("function", {}).get("name", ""),
                                                "arguments": tc.get("function", {}).get("arguments", "")
                                            }
                                        }
                                    else:
                                        if "name" in tc.get("function", {}):
                                            current_tool_calls[idx]["function"]["name"] += tc["function"]["name"]
                                        if "arguments" in tc.get("function", {}):
                                            current_tool_calls[idx]["function"]["arguments"] += tc["function"]["arguments"]
                        except json.JSONDecodeError:
                            logger.error("Failed to parse LLM stream chunk", chunk=data_str)
                            
        # If we finished and have tool calls, yield them
        if current_tool_calls:
            for tc in current_tool_calls.values():
                yield {"type": "tool_call", "tool_call": tc}
                
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error from LLM: {e.response.text}")
    except Exception as e:
        logger.exception(f"Error calling LLM: {e}")
