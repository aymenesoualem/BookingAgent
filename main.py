import os
import json
import base64
import asyncio
import websockets
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import JSONResponse
from fastapi.websockets import WebSocketDisconnect
from starlette.responses import HTMLResponse
from twilio.twiml.voice_response import VoiceResponse, Connect, Say, Stream
from dotenv import load_dotenv
from bookings import book_room, get_available_rooms
import ssl
import inspect
from typing import List, Dict, Any
from datetime import date



def book_room_function(hotel_name: str, room_number: str, customer_name: str, check_in: date, check_out: date):
    """This function books a room, call this function when the user wants to book a room."""
    return book_room(hotel_name, room_number, customer_name, check_in, check_out)

def get_available_rooms_function(check_in: date, check_out: date, room_type: str = None, max_guests: int = None):
    """This function returns available rooms, call this function when the user wants to check for available rooms."""
    return get_available_rooms(check_in, check_out,room_type, max_guests)



def function_to_schema(func) -> str:
    """
    Converts a Python function's signature into a schema format suitable for OpenAI Realtime API
    and returns it as a JSON string.
    """
    # Mapping Python types to OpenAI API types
    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
        type(None): "null",
        date: "string",  # Represent date as a string in ISO 8601 format
        List: "array",  # Handle List type
        Dict: "object",  # Handle Dict type
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

        param_info = {"type": param_type}

        # Check if the parameter is a date type and add format
        if param.annotation == date:
            param_info["format"] = "date"

        # Handle more complex types (e.g., List, Dict)
        if hasattr(param.annotation, "__origin__"):
            if param.annotation.__origin__ == list:
                param_info["items"] = {"type": "string"}  # Example for List, could be customized
            elif param.annotation.__origin__ == dict:
                param_info["additionalProperties"] = {"type": "string"}  # Example for Dict

        parameters[param.name] = param_info

    # Identify required parameters (those without a default value)
    required = [
        param.name
        for param in signature.parameters.values()
        if param.default == inspect._empty
    ]

    # Build the function schema
    schema = {
        "type": "function",
        "name": func.__name__,
        "description": (func.__doc__ or "").strip(),
        "parameters": {
            "type": "object",
            "properties": parameters,
            "required": required,
        },
    }

    # Return the schema as a JSON string
    return json.dumps(schema, indent=2)

tools= [book_room_function, get_available_rooms_function]
tool_schemas = "[" + ",\n".join(function_to_schema(tool) for tool in tools) + "]"
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

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.getenv("PORT", 5050))
system_message = """
You are a multilingual AI assistant capable of understanding and communicating in various languages and specializing in providing seamless hotel booking and support services in Morocco through natural and engaging conversations. Your primary tasks include:
1. Assisting users in searching for and booking hotels, offering personalized recommendations, managing bookings, and providing instant confirmations or modifications.
2. Offering on-site support such as assistance with check-in/check-out, handling service requests, and providing local recommendations for attractions, dining, and transportation.
3. Supporting multilingual interactions by communicating fluently in various languages including Arabic, French, English, and Moroccan Darija, and offering real-time translation between users and hotel staff.
4. Leveraging generative AI to deliver quick, accurate, and contextually appropriate responses.
5. Integrating smoothly with hotel management systems to provide consistent and reliable information.
6. Based on the user’s language, respond in the same language.
Your tone should be professional, friendly, and customer-focused, ensuring users feel supported and valued at every step. Additionally, emphasize the benefits of enhanced customer experience, operational efficiency, and global accessibility in all interactions.

When the user asks for a service that involves invoking a function (e.g., booking a room, retrieving available rooms), respond in the following format:

    function: "<function_name>", parameters: <parameters_as_dict>

For example:
    function: "book_room_function", parameters: {"hotel_name": "Hotel XYZ", "room_number": "101", "customer_name": "John Doe", "check_in": "2025-01-10", "check_out": "2025-01-12"}

Once the model returns the above output, it will automatically invoke the respective function through `handle_tool_invocation` and process the user's request. If there is no tool invocation, simply respond with the appropriate text.

You have access to the following functions:"""+tool_schemas+"""".
If you ever need to invoke any function, always format it as described above, and ensure it is routed to the `handle_tool_invocation` function.
Only specify the function call in the response.done event
Adapt your approach to cater to other potential sectors like healthcare (e.g., appointment scheduling), transportation hubs (e.g., airports or train stations), or similar industries requiring conversational support. Be mindful of cultural nuances and the specific context of the user's needs.
"""

VOICE= 'alloy'
LOG_EVENT_TYPES = [
    'error', 'response.content.done', 'rate_limits.updated',
    'response.done', 'input_audio_buffer.committed',
    'input_audio_buffer.speech_stopped', 'input_audio_buffer.speech_started',
    'session.created','function_call_arguments.done'
]
SHOW_TIMING_MATH = False
app = FastAPI()

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not set")

@app.get("/",response_class=JSONResponse)
async def index_page():
    return {"message":"Server is running"}

@app.api_route("/incoming-call", methods=["GET", "POST"])
async def handle_incoming_call(request: Request):
    """Handle incoming call and return TwiML response to connect to Media Stream."""
    response = VoiceResponse()
    # <Say> punctuation to improve text-to-speech flow
    response.say("Please wait while we connect your call to the A. I. Booking assistant. ")
    response.pause(length=1)
    response.say("O.K. you can start talking!")
    host = request.url.hostname
    connect = Connect()
    connect.stream(url=f'wss://{host}/media-stream')
    response.append(connect)
    return HTMLResponse(content=str(response), media_type="application/xml")


@app.websocket("/media-stream")
async def handle_media_stream(websocket: WebSocket):
    """Handle WebSocket connections between Twilio and OpenAI."""
    print("Client connected")
    await websocket.accept()
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    async with websockets.connect(
            'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01',
            ssl=ssl_context,
            extra_headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "OpenAI-Beta": "realtime=v1"
            }
    ) as openai_ws:
        await initialize_session(openai_ws)

        # Connection specific state
        stream_sid = None
        latest_media_timestamp = 0
        last_assistant_item = None
        mark_queue = []
        response_start_timestamp_twilio = None

        async def receive_from_twilio():
            """Receive audio data from Twilio and send it to the OpenAI Realtime API."""
            nonlocal stream_sid, latest_media_timestamp
            try:
                async for message in websocket.iter_text():
                    data = json.loads(message)
                    if data['event'] == 'media' and openai_ws.open:
                        latest_media_timestamp = int(data['media']['timestamp'])
                        audio_append = {
                            "type": "input_audio_buffer.append",
                            "audio": data['media']['payload']
                        }
                        await openai_ws.send(json.dumps(audio_append))
                    elif data['event'] == 'start':
                        stream_sid = data['start']['streamSid']
                        print(f"Incoming stream has started {stream_sid}")
                        response_start_timestamp_twilio = None
                        latest_media_timestamp = 0
                        last_assistant_item = None
                    elif data['event'] == 'mark':
                        if mark_queue:
                            mark_queue.pop(0)
            except WebSocketDisconnect:
                print("Client disconnected.")
                if openai_ws.open:
                    await openai_ws.close()

        async def send_to_twilio():
            """Receive events from the OpenAI Realtime API, send audio back to Twilio."""
            nonlocal stream_sid, last_assistant_item, response_start_timestamp_twilio
            try:
                async for openai_message in openai_ws:
                    response = json.loads(openai_message)
                    if response['type'] in LOG_EVENT_TYPES:
                        print(f"Received event: {response['type']}", response)


                    if response.get('type') == 'response.audio.delta' and 'delta' in response:
                        audio_payload = base64.b64encode(base64.b64decode(response['delta'])).decode('utf-8')
                        audio_delta = {
                            "event": "media",
                            "streamSid": stream_sid,
                            "media": {
                                "payload": audio_payload
                            }
                        }
                        await websocket.send_json(audio_delta)

                        if response_start_timestamp_twilio is None:
                            response_start_timestamp_twilio = latest_media_timestamp
                            if SHOW_TIMING_MATH:
                                print(f"Setting start timestamp for new response: {response_start_timestamp_twilio}ms")

                        # Update last_assistant_item safely
                        if response.get('item_id'):
                            last_assistant_item = response['item_id']

                        await send_mark(websocket, stream_sid)

                    # Trigger an interruption. Your use case might work better using `input_audio_buffer.speech_stopped`, or combining the two.
                    if response.get('type') == 'input_audio_buffer.speech_started':
                        print("Speech started detected.")
                        if last_assistant_item:
                            print(f"Interrupting response with id: {last_assistant_item}")
                            await handle_speech_started_event()

                    if response.get('type') == 'response.done':
                        # Safely extract the transcript if output is available
                        output = response['response'].get('output', [])
                        if output:
                            message = output[0]['content'][0].get('transcript', "No transcript available")
                            await process_model_output(message)
                            print(f"Received response: {message}")
                        else:
                            print("No output in response.done")
            except Exception as e:
                print(f"Error in send_to_twilio: {e}")

        async def handle_speech_started_event():
            """Handle interruption when the caller's speech starts."""
            nonlocal response_start_timestamp_twilio, last_assistant_item
            print("Handling speech started event.")
            if mark_queue and response_start_timestamp_twilio is not None:
                elapsed_time = latest_media_timestamp - response_start_timestamp_twilio
                if SHOW_TIMING_MATH:
                    print(
                        f"Calculating elapsed time for truncation: {latest_media_timestamp} - {response_start_timestamp_twilio} = {elapsed_time}ms")

                if last_assistant_item:
                    if SHOW_TIMING_MATH:
                        print(f"Truncating item with ID: {last_assistant_item}, Truncated at: {elapsed_time}ms")

                    truncate_event = {
                        "type": "conversation.item.truncate",
                        "item_id": last_assistant_item,
                        "content_index": 0,
                        "audio_end_ms": elapsed_time
                    }
                    await openai_ws.send(json.dumps(truncate_event))

                await websocket.send_json({
                    "event": "clear",
                    "streamSid": stream_sid
                })

                mark_queue.clear()
                last_assistant_item = None
                response_start_timestamp_twilio = None

        async def send_mark(connection, stream_sid):
            if stream_sid:
                mark_event = {
                    "event": "mark",
                    "streamSid": stream_sid,
                    "mark": {"name": "responsePart"}
                }
                await connection.send_json(mark_event)
                mark_queue.append('responsePart')

        await asyncio.gather(receive_from_twilio(), send_to_twilio())

async def send_initial_conversation_item(openai_ws):
    """Send initial conversation item if AI talks first."""
    initial_conversation_item = {
        "type": "conversation.item.create",
        "item": {
            "type": "message",
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": "Greet the user with 'Hello there! I am an AI voice assistant powered by Twilio and the OpenAI Realtime API. You can ask me for facts, jokes, or anything you can imagine. How can I help you?'"
                }
            ]
        }
    }
    await openai_ws.send(json.dumps(initial_conversation_item))
    await openai_ws.send(json.dumps({"type": "response.create"}))

async def initialize_session(openai_ws):
    """Control initial session with OpenAI."""
    session_update = {
        "type": "session.update",
        "session": {
            "turn_detection": {"type": "server_vad"},
            "input_audio_format": "g711_ulaw",
            "output_audio_format": "g711_ulaw",
            "voice": VOICE,
            "instructions": system_message,
            "modalities": ["text", "audio"],
            "temperature": 0.8,
        }
}



    print('Sending session update:', json.dumps(session_update))
    await openai_ws.send(json.dumps(session_update))

    # Uncomment the next line to have the AI speak first
    await send_initial_conversation_item(openai_ws)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
