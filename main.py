import os
import json
import base64
import asyncio
import websockets
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import JSONResponse
from fastapi.websockets import WebSocketDisconnect
from starlette.responses import HTMLResponse
from twilio.twiml.voice_response import VoiceResponse, Connect
from dotenv import load_dotenv

from agents.agent import initialize_session, LOG_EVENT_TYPES
import ssl


from tools.functioncalling import invoke_function

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.getenv("PORT", 5050))

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
    # Get the caller's phone number from the "From" parameter
    # Read the form data from the incoming request
    form = await request.form()

    # Extract caller's phone number (From) and other parameters
    from_number = form.get("From")  # Caller’s phone number
    to_number = form.get("To")  # Twilio phone number
    call_sid = form.get("CallSid")  # Unique identifier for the call

    # Log the caller's phone number for debugging purposes
    print(f"Call received from: {from_number}")
    print(f"Call SID: {call_sid}")
    print(f"Twilio number: {to_number}")
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
    system_message = """
    You are a multilingual AI assistant specializing in providing seamless hotel booking and support services in Morocco through natural and engaging conversations. Your primary tasks include:

    1. Assisting users in searching for and booking hotels, offering personalized recommendations, managing bookings, and providing instant confirmations or modifications.
    2. Offering on-site support such as assistance with check-in/check-out, handling service requests, and providing local recommendations for attractions, dining, and transportation.
    3. Supporting multilingual interactions by communicating fluently in Arabic, French, English, and Moroccan Darija, and offering real-time translation between users and hotel staff.
    4. Leveraging generative AI to deliver quick, accurate, and contextually appropriate responses.
    5. Integrating smoothly with hotel management systems to provide consistent and reliable information.
    6. Ensuring responses align with the user’s preferred language.

    ### Hotel Directory
    You have access to the following hotels and their locations:
    - Hotel Atlas: Marrakech
    - Hotel Saadien: Casablanca
    - Hotel Imperial: Fez
    - Hotel Medina: Rabat
    - Hotel Oasis: Agadir
    - Hotel Al-Bahr: Tangier

    When a user requests a service involving a function invocation (e.g., booking a room, retrieving available rooms):
    - Use the hotel directory to refine recommendations based on the location or area provided by the user.
    - Provide clear, user-friendly outputs that simplify the booking process.

    When the user asks for places or things to do around the hotel’s area, scrape the web using the web scraper tool to give them some recommendations.

    ### Customer Interaction
    At the start of each interaction, always ask for the customer’s name before proceeding with the booking. For example:
    "Bonjour, veuillez me fournir votre nom complet pour que je puisse commencer votre réservation."

    ### Tone and Approach
    Maintain a professional, friendly, and customer-focused tone to ensure users feel supported and valued. Emphasize the benefits of enhanced customer experience, operational efficiency, and global accessibility in all interactions.

    ### Additional Adaptability
    Adapt your approach to cater to other sectors such as healthcare (e.g., appointment scheduling) or transportation hubs (e.g., airport support). Always be mindful of cultural nuances and user context.
    """
    initial_message = "Greet the user with 'Hello there! I am an AI voice assistant for Moravelo Hotel Group where comfort meets elegance.' repeat the message in French then in Arabic."

    async with websockets.connect(
            'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01',
            ssl=ssl_context,
            extra_headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "OpenAI-Beta": "realtime=v1"
            }
    ) as openai_ws:
        await initialize_session(openai_ws,system_message=system_message,initial_message=initial_message)

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

                    if response.get('type') == 'response.done':
                        # Safely extract the transcript if output is available
                        output = response['response'].get('output', [])
                        if output:
                            for item in output:
                                if item.get('type') == 'function_call':
                                    function_name = item.get('name')
                                    arguments = json.loads(item.get('arguments', "{}"))
                                    call_id = item.get('call_id')

                                    print(f"Detected function call: {function_name} with arguments: {arguments}")
                                    result = await invoke_function(function_name, arguments)
                                    # Send function_call_output to OpenAI
                                    await openai_ws.send(json.dumps({
                                        "type": "conversation.item.create",
                                        "item": {
                                            "type": "function_call_output",
                                            "call_id": call_id,
                                            "output": json.dumps(result)
                                        }
                                    }))
                                    await openai_ws.send(json.dumps({"type": "response.create"}))



                        else:
                            print("No output in response.done")

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



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
