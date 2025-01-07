import os
import json
import asyncio
import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
import ssl
from main import tools, function_to_schema, book_room_function, get_available_rooms_function

# Generate tool schemas
tool_schemas = "[" + ",\n".join(function_to_schema(tool) for tool in tools) + "]"
print(tool_schemas)

system_message = """
You are a multilingual AI assistant specializing in providing seamless hotel booking and support services through natural and engaging conversations. Your primary tasks include:
1. Assisting users in searching for and booking hotels, offering personalized recommendations, managing bookings, and providing instant confirmations or modifications.
2. Offering on-site support such as assistance with check-in/check-out, handling service requests, and providing local recommendations for attractions, dining, and transportation.
3. Supporting multilingual interactions by communicating fluently in various languages and offering real-time translation between users and hotel staff.
4. Leveraging generative AI to deliver quick, accurate, and contextually appropriate responses.
5. Integrating smoothly with hotel management systems to provide consistent and reliable information.

Your tone should be professional, friendly, and customer-focused, ensuring users feel supported and valued at every step. Additionally, emphasize the benefits of enhanced customer experience, operational efficiency, and global accessibility in all interactions.

When the user asks for a service that involves invoking a function (e.g., booking a room, retrieving available rooms), respond in the following format:

    function: "<function_name>", parameters: {"key1": "value1", "key2": "value2"}

For example:
    function: "book_room_function", parameters: {"hotel_name": "Hotel XYZ", "room_number": "101", "customer_name": "John Doe", "check_in": "2025-01-10", "check_out": "2025-01-12"}

Once the model returns the above output, it will automatically invoke the respective function through `handle_tool_invocation` and process the user's request. If there is no tool invocation, simply respond with the appropriate text.

You have access to the following functions: """+tool_schemas+""".
If you ever need to invoke any function, always format it as described above, and ensure it is routed to the `handle_tool_invocation` function.
"""

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Function to handle tool invocation
async def handle_tool_invocation(function_name: str, parameters: dict):
    """Call the relevant function based on the tool invocation."""

    # Dynamically fetch the function by name and call it with the parameters
    function_map = {
        "book_room_function": book_room_function,
        "get_available_rooms_function": get_available_rooms_function
        # Add more functions here as needed
    }

    function = function_map.get(function_name)

    if function:
        # Call the function with parameters (unpack the dictionary into function arguments)
        return await function(**parameters)
    else:
        return f"Unknown function requested: {function_name}"


async def process_model_output(model_response: str):
    """Process the model output and check if it includes a tool invocation."""
    if "function:" in model_response:
        # Extract function name and parameters from the model response
        try:
            import ast
            # Extract the function call
            function_name_start = model_response.find("function:") + len("function:")
            parameters_start = model_response.find("parameters:") + len("parameters:")

            function_name = model_response[function_name_start:parameters_start].strip().strip('"')
            parameters_str = model_response[parameters_start:].strip()
            parameters = ast.literal_eval(parameters_str)  # Safely parse the parameters as a dictionary

            # Invoke the tool through the handle_tool_invocation function
            return await handle_tool_invocation(function_name, parameters)
        except Exception as e:
            return f"Error parsing model output: {str(e)}"
    else:
        # If it's not a tool invocation, return the normal response
        return model_response


# FastAPI app setup
app = FastAPI()

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        # WebSocket URI for testing
        uri = 'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01'
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        # Define headers
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }

        # Connect to the external WebSocket
        async with websockets.connect(uri, ssl=ssl_context, extra_headers=headers) as external_websocket:
            print("Connected to OpenAI WebSocket")

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
                }
            }
            await external_websocket.send(json.dumps(session_update))
            print("Session initialized")

            # Listen for incoming messages from the client
            while True:
                message = await websocket.receive_text()
                print(f"Received message from client: {message}")
                user_message = message  # Use the actual received message

                # Send a test message to the external WebSocket
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
                await external_websocket.send(json.dumps(conversation_item))
                print(f"Message sent to OpenAI WebSocket: {user_message}")

                # Receive the response from the external WebSocket
                response = await external_websocket.recv()
                response_data = json.loads(response)

                print(f"Received response data: {response_data}")  # Added log

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

                # If a function call is made
                if response_data.get('type') == 'function_call':
                    function_name = response_data['function_call']['name']
                    parameters = response_data['function_call']['parameters']
                    result = await handle_tool_invocation(function_name, parameters)

                    # Send function result back to WebSocket
                    result_message = {
                        "type": "conversation.item.create",
                        "item": {
                            "type": "message",
                            "role": "system",
                            "content": [
                                {"type": "input_text", "text": result}
                            ]
                        }
                    }
                    await external_websocket.send(json.dumps(result_message))
                    print(f"Function result sent: {result}")

                elif agent_response:
                    print(f"Agent response: {agent_response}")
                    await websocket.send_text(agent_response)
                else:
                    print(f"No agent response found, full response: {response_data}")
                    await websocket.send_text(json.dumps(response_data))

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error: {str(e)}")

# Start the FastAPI app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
