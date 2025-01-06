import inspect
import os
import json
import asyncio
import websockets
from dotenv import load_dotenv
from datetime import date
import ssl

from bookings import get_available_rooms, book_room


def book_room_function(room_number: str, customer_name: str, check_in: date, check_out: date):
    """This function books a room, call this function when the user wants to book a room."""
    return book_room(room_number, customer_name, check_in, check_out)

def get_available_rooms_function(check_in: date, check_out: date):
    """This function returns available rooms, call this function when the user wants to check for available rooms."""
    return get_available_rooms(check_in, check_out)

def function_to_schema(func) -> dict:
    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
        type(None): "null",
    }

    try:
        signature = inspect.signature(func)
    except ValueError as e:
        raise ValueError(
            f"Failed to get signature for function {func.__name__}: {str(e)}"
        )

    parameters = {}
    for param in signature.parameters.values():
        try:
            param_type = type_map.get(param.annotation, "string")
        except KeyError as e:
            raise KeyError(
                f"Unknown type annotation {param.annotation} for parameter {param.name}: {str(e)}"
            )
        parameters[param.name] = {"type": param_type}

    required = [
        param.name
        for param in signature.parameters.values()
        if param.default == inspect._empty
    ]

    return {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": (func.__doc__ or "").strip(),
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": required,
            },
        },
    }

tools= [book_room_function, get_available_rooms_function]
tool_schemas = [function_to_schema(tool) for tool in tools]
print(tool_schemas)
# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not set")

async def test_websocket():
    try:
        # WebSocket URI
        uri = 'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01'
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        # Define headers
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }

        # Use the connect function with headers directly
        async with websockets.connect(uri,ssl=ssl_context, additional_headers=headers) as websocket:
            print("Connected to WebSocket")

            # Initialize the session
            session_update = {
                "type": "session.update",
                "session": {
                    "turn_detection": {"type": "server_vad"},
                    "input_audio_format": "g711_ulaw",
                    "output_audio_format": "g711_ulaw",
                    "voice": "alloy",
                    "instructions": "System message",
                    "modalities": ["text", "audio"],  # Updated to include audio modality
                    "temperature": 0.8,
                    "tools": tool_schemas,  # Corrected to pass tool_schemas directly
                }
            }
            await websocket.send(json.dumps(session_update))
            print("Session initialized")

            # Send a test message
            user_message = "Hello, agent!"
            conversation_item = {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": user_message}
                    ]
                }
            }
            await websocket.send(json.dumps(conversation_item))
            print(f"Message sent: {user_message}")

            # Receive the response
            response = await websocket.recv()
            print(f"Response: {response}")

    except Exception as e:
        print(f"Error: {str(e)}")

# Run the WebSocket test
if __name__ == "__main__":
    asyncio.run(test_websocket())
