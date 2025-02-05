import os
from datetime import date
from typing import Optional, List
import psycopg2
from fastapi import FastAPI, WebSocket, Request, HTTPException
from fastapi.params import Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, joinedload
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse
from twilio.twiml.voice_response import VoiceResponse, Connect
from dotenv import load_dotenv
from agents.agent import  handle_call
from outboundcall import make_call
from tools.functioncalling import inbound_caller_tool_schemas, outbound_caller_tool_schemas

load_dotenv()
PORT = int(os.getenv("PORT", 5050))

SHOW_TIMING_MATH = False
app = FastAPI()
class Booking(BaseModel):
    id: str
    customer_name: str
    room_number: str
    check_in_date: date
    check_out_date: date
    phone_number: str
    feedback: str

    class Config:
        from_attributes = True



app = FastAPI()

# Database configuration
DATABASE_URL = "postgresql://agent:booking@localhost:5432/Hotel_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


# Dependency to get the DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


from fastapi.logger import logger


from typing import List

# Database connection function using psycopg2
def get_db_connection():
    try:
        connection = psycopg2.connect(DATABASE_URL)
        return connection
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {e}")

@app.get("/bookings", response_model=List[Booking])
def get_bookings():
    try:
        # Establish database connection
        connection = get_db_connection()
        cursor = connection.cursor()

        # Query to join bookings and rooms
        query = """
        SELECT 
            b.id AS booking_id,
            c.name AS customer_name,
            r.room_number,
            b.check_in_date,
            b.check_out_date,
            c.phone_number AS customer_number,
            b.feedback
        FROM 
            bookings b
        JOIN 
            customers c ON b.customer_id = c.id
        JOIN 
            rooms r ON b.room_id = r.id;
        """

        # Execute query
        cursor.execute(query)
        result = cursor.fetchall()

        # Process the data
        bookings = []
        for row in result:
            # Map result to a dictionary that matches the structure of the Booking model
            bookings.append({
                "id": row[0],
                "customer_name": row[1],
                "room_number": row[2],
                "check_in_date": row[3].strftime('%Y-%m-%d'),  # Formatting the date to string
                "check_out_date": row[4].strftime('%Y-%m-%d'),  # Formatting the date to string
                "phone_number": row[5] , # Using the hardcoded phone number
                "feedback": row[6]
            })

        # Close the cursor and connection
        cursor.close()
        connection.close()

        if not bookings:
            raise HTTPException(status_code=404, detail="No bookings found!")

        # Return JSON response with the data
        return JSONResponse(content=bookings)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching bookings: {e}")
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

    ### Hotel Booking Services
    - Assist users in searching for and booking hotels.
    - Offer personalized recommendations based on user preferences and the Hotel Directory.
    - Manage bookings, including modifications and cancellations, with instant confirmations.
    - Retrieve customer details using their phone number. If the customer doesn’t exist, seamlessly create a new customer profile.

    ### On-Site Support
    - Help with check-in/check-out procedures.
    - Handle service requests such as room upgrades or special accommodations.
    - Provide local recommendations for attractions, dining, and transportation near the hotel.

    ### Multilingual Communication
    - Communicate fluently in Arabic, French, English, and Moroccan Darija.
    - Facilitate real-time translation between users and hotel staff when needed.

    ### AI-Powered Responses
    - Leverage generative AI to provide fast, accurate, and contextually relevant responses.
    - Ensure all responses align with the user’s preferred language.

    ### Hotel Management System Integration
    - Seamlessly connect with hotel management systems to ensure consistent and reliable information.

    ### Hotel Directory
    You have access to the following hotels and their locations:
    - **Hotel Atlas**: Marrakech
    - **Hotel Saadien**: Casablanca
    - **Hotel Imperial**: Fez
    - **Hotel Medina**: Rabat
    - **Hotel Oasis**: Agadir
    - **Hotel Al-Bahr**: Tangier

    ### Booking Process
    When users request booking services:
    - First, retrieve the customer’s details using their phone number.
      - Use the `get_customer_function` to find customer details.
      - If the customer doesn’t exist, create a new customer profile using the `add_customer_function`.
    - Use the Hotel Directory to refine recommendations based on the user's desired location.
    - Room types in the database:
        - **Single**: $60.00
        - **Double**: $100.00
        - **Suite**: $180.00
        - **Deluxe**: $250.00
    - Provide clear and user-friendly booking outputs to simplify the process.

    ### Local Recommendations
    For requests about nearby attractions or activities:
    - Use the `webscraper_for_recommendations_function` to retrieve and share up-to-date recommendations tailored to the hotel’s area.

    ### Customer Interaction
    - Always begin each interaction by retrieving the customer’s details using their phone number.
      - If no details are found, create a new customer profile.
    - Greet the customer by requesting their name. For example:
      "Bonjour, veuillez me fournir votre nom complet pour que je puisse commencer votre réservation."

    ### Tools Available
    You can use the following tools to support your tasks:
    1. **`book_room_function`**: Book a hotel room for the customer.
    2. **`get_available_rooms_function`**: Retrieve available rooms based on criteria.
    3. **`webscraper_for_recommendations_function`**: Fetch recommendations for attractions and activities.
    4. **`delete_booking_function`**: Cancel an existing booking.
    5. **`alter_booking_function`**: Modify an existing booking.
    6. **`find_booking_by_number_function`**: Retrieve details of a booking using the booking number.
    7. **`hangup_function`**: End the session once the conversation is over.
    8. **`knowledgebase_retrieval_function`**: Access the knowledge base to provide detailed hotel-related information.
    9. **`get_customer_function`**: Retrieve customer details using their phone number.
    10. **`add_customer_function`**: Add a new customer to the system if they don’t exist.

    ### Tone and Approach
    - Maintain a professional, friendly, and customer-focused tone.
    - Highlight the benefits of enhanced customer experience, operational efficiency, and global accessibility.
    - Be mindful of cultural nuances and user context.

    ### Adaptability
    In addition to hotel services, adapt your approach to support sectors like healthcare (e.g., appointment scheduling) or transportation hubs (e.g., airport assistance).

    ### Customer Number
    The customer's number for this session is: """ + customer_number + """
    When the conversation is over, invoke the `hangup_function`.
    """

    initial_message = "Greet the user with 'Hello there! I am an AI voice assistant for Moravelo Hotel Group where comfort meets elegance.' repeat the message in French then in Arabic."


    await handle_call(websocket,system_message,initial_message,inbound_caller_tool_schemas)

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
    The customer's number for this session is: """+customer_number +"""
    
    """

    initial_message = "Greet the user with 'Hello there! I am an AI voice assistant for Moravelo Hotel Group where comfort meets elegance.' repeat the message in French then in Arabic."


    await handle_call(websocket,system_message,initial_message,outbound_caller_tool_schemas)
# Example model for request body
class OutboundCallRequest(BaseModel):
    phone_number: str


# POST endpoint for initiating an outbound call
@app.get("/outbound-call/{phone_number}")
async def get_outbound_call(phone_number: str):
    try:
        response = await make_call(phone_number)
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
