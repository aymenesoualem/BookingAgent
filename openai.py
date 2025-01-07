import inspect
import os
import json
import asyncio
import websockets
from dotenv import load_dotenv
import ssl

from main import tools, function_to_schema, system_message

# Generate tool schemas
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

        # Connect to the WebSocket
        async with websockets.connect(uri, ssl=ssl_context, additional_headers=headers) as websocket:
            print("Connected to WebSocket")

            # Initialize the session
            session_update = {
                "type": "session.update",
                "session": {
                    "turn_detection": {"type": "server_vad"},
                    "input_audio_format": "g711_ulaw",
                    "output_audio_format": "g711_ulaw",
                    "voice": "alloy",
                    "instructions": system_message,
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
            response_data = json.loads(response)

            # Extract the agent's response
            agent_response = None
            if (
                "type" in response_data
                and response_data["type"] == "conversation.item.create"
                and "item" in response_data
                and "content" in response_data["item"]
            ):
                agent_response = next(
                    (item["text"] for item in response_data["item"]["content"] if item["type"] == "input_text"),
                    None
                )

            if agent_response:
                print(f"Agent Response: {agent_response}")
            else:
                print(f"Full Response: {response_data}")

    except Exception as e:
        print(f"Error: {str(e)}")

# Run the WebSocket test
if __name__ == "__main__":
    asyncio.run(test_websocket())
