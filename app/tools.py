import structlog

logger = structlog.get_logger(__name__)

# Sample mock tools

async def lookup_order_status(order_id: str) -> str:
    """Looks up the status of an order."""
    logger.info("Tool called: lookup_order_status", order_id=order_id)
    return f"Order {order_id} is currently being shipped and will arrive tomorrow."

async def book_appointment(date: str, time: str) -> str:
    """Books an appointment for the user."""
    logger.info("Tool called: book_appointment", date=date, time=time)
    return f"Appointment booked successfully for {date} at {time}."

async def transfer_to_human(reason: str) -> str:
    """Transfers the call to a human agent."""
    logger.info("Tool called: transfer_to_human", reason=reason)
    return "TRANSFER_INITIATED"

async def end_call(reason: str) -> str:
    """Ends the phone call."""
    logger.info("Tool called: end_call", reason=reason)
    return "CALL_ENDED"

# OpenAI-compatible tool schemas
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "lookup_order_status",
            "description": "Looks up the status of a user's order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The alphanumeric order ID."
                    }
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Books a service appointment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "The date for the appointment (e.g. 2026-10-15)"
                    },
                    "time": {
                        "type": "string",
                        "description": "The time for the appointment (e.g. 14:00)"
                    }
                },
                "required": ["date", "time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "transfer_to_human",
            "description": "Transfers the call to a human agent if the user requests it or if the agent cannot help.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "The reason for the transfer."
                    }
                },
                "required": ["reason"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "end_call",
            "description": "Ends the call gracefully after saying goodbye.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "The reason for ending the call."
                    }
                },
                "required": ["reason"]
            }
        }
    }
]

def execute_tool(name: str, arguments: dict) -> str:
    # Synchronous wrapper for simplicity, in real app use async if needed
    if name == "lookup_order_status":
        return f"Order {arguments.get('order_id')} is currently being shipped and will arrive tomorrow."
    elif name == "book_appointment":
        return f"Appointment booked successfully for {arguments.get('date')} at {arguments.get('time')}."
    elif name == "transfer_to_human":
        return "TRANSFER_INITIATED"
    elif name == "end_call":
        return "CALL_ENDED"
    else:
        return f"Error: Tool {name} not found."
