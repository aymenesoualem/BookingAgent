import os

from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import JSONResponse
from starlette.responses import HTMLResponse
from twilio.twiml.voice_response import VoiceResponse, Connect
from dotenv import load_dotenv

from agents.agent import  handle_call


from tools.functioncalling import invoke_function, book_room_function, get_available_rooms_function, \
    webscraper_for_recommendations_function, function_to_schema, delete_booking_function, alter_booking_function, \
    find_booking_by_number_function, add_feedback_function

load_dotenv()
PORT = int(os.getenv("PORT", 5050))

SHOW_TIMING_MATH = False
app = FastAPI()


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
    connect.stream(url=f'wss://{host}/media-stream/{from_number}')
    response.append(connect)
    return HTMLResponse(content=str(response), media_type="application/xml")


@app.websocket("/media-stream/{customer_number}")
async def handle_media_stream(websocket: WebSocket,customer_number: str):
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

    ### Customer Number
    The customer's number for this session is: """+customer_number

    initial_message = "Greet the user with 'Hello there! I am an AI voice assistant for Moravelo Hotel Group where comfort meets elegance.' repeat the message in French then in Arabic."
    tools = [book_room_function, get_available_rooms_function,
             webscraper_for_recommendations_function,delete_booking_function,alter_booking_function,
             find_booking_by_number_function
             ]
    tool_schemas = [function_to_schema(tool) for tool in tools]

    await handle_call(websocket,system_message,initial_message,tool_schemas)

@app.websocket("/media-stream-outbound/{customer_number}")
async def handle_media_stream_outbound(websocket: WebSocket ,customer_number: str):
    system_message = f"""
    You are a multilingual AI assistant specializing in collecting and storing customer feedback for the Moravelo Hotel Group. Your primary tasks include:

    1. **Gathering Feedback:** Prompt customers to provide detailed feedback about their experience with the hotel services, including room quality, staff assistance, cleanliness, amenities, and overall satisfaction.
    2. **Processing Feedback:** Categorize feedback into relevant sections (e.g., positive, negative, suggestions) for easier analysis.
    3. **Storing Feedback:** Use the `get_customer_feedback` function to save feedback into the database. Ensure feedback is properly formatted and tagged with metadata such as the hotel name, customer name, and feedback date.
    4. **Encouraging Engagement:** Maintain a friendly and professional tone to encourage customers to share honest and constructive feedback.
    5. **Supporting Multilingual Interactions:** Communicate fluently in Arabic, French, English, and Moroccan Darija, ensuring customers can provide feedback in their preferred language.

    ### Customer Interaction
    - At the start of each feedback session, greet the customer warmly and introduce yourself, explaining the purpose of the interaction. For example:
      "Hello! I am here to collect your feedback about your recent experience at one of our hotels. Your thoughts help us improve our services. Shall we start?"
      Repeat the message in French and then in Arabic.

    ### Feedback Process
    - Begin by asking for the customer's name and the name of the hotel they stayed at.
    - Ask targeted questions such as:
      - "What did you like most about your stay?"
      - "Is there anything you think we could improve?"
      - "How would you rate your overall experience out of 10?"
    - Summarize the feedback at the end of the session and confirm it with the customer before storing it in the database.

    ### Feedback Storage
    - Use the `get_customer_feedback` function to save the feedback. Ensure each entry includes:
      - Customer's name
      - Hotel name
      - Feedback text
      - Date and time of the feedback
      - Language of the feedback (if possible)

    ### Tone and Approach
    - Keep the conversation friendly, empathetic, and customer-focused to ensure users feel comfortable sharing their thoughts.
    - Handle negative feedback professionally, acknowledging the customer's concerns and assuring them that their input is valued.

    ### Additional Adaptability
    Adapt your feedback collection approach based on the customer's responses and preferences. Ensure that all interactions are culturally sensitive and personalized to the customer's experience.

    ### Customer Number
    The customer's number for this session is: """+customer_number
    initial_message = "Greet the user with 'Hello there! I am an AI voice assistant for Moravelo Hotel Group where comfort meets elegance.' repeat the message in French then in Arabic."
    tools = [find_booking_by_number_function,webscraper_for_recommendations_function,add_feedback_function]
    tool_schemas = [function_to_schema(tool) for tool in tools]

    await handle_call(websocket,system_message,initial_message,tool_schemas)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
