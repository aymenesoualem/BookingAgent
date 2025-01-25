import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.header import Header

from twilio.twiml.voice_response import VoiceResponse

from rag.kdb import init_chromadb_client, retrieve_info
from templates.email_template import BOOKING_EMAIL_TEMPLATE
from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey, Numeric, Boolean, TIMESTAMP, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import sys
from datetime import date, datetime
import os

from dotenv import load_dotenv
from tavily import TavilyClient
from twilio.rest import Client
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

def web_scraper_for_recommendation(topic:str):
    client = TavilyClient(api_key=os.getenv('API_KEY'))
    response = client.search(topic)
    return  response.get('results')


def send_sms(to: str, body: str):
    """Send an SMS using Twilio."""
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    from_number = os.getenv('TWILIO_FROM_NUMBER')
    # Initialize Twilio client
    client = Client(account_sid, auth_token)

    # Send SMS
    message = client.messages.create(
        body=body,  # SMS body/content
        from_=from_number,  # Your Twilio phone number
        to=to  # Recipient phone number
    )

    # Print message SID (optional for tracking)
    print(f"Message SID: {message.sid}")

    return message.sid  # Return the SID of the sent message for reference

# if __name__ == '__main__':
#     send_sms("+212679675314","Hi")
#     result = web_scraper_for_recommendation("Nice things to do in casa")
#     print (result)

load_dotenv()

def send_email_with_banner(hotel_name, room_number, customer_name, check_in, check_out):
    """Send a booking confirmation email with the banner image."""
    try:
        from_email = os.getenv("FROM_EMAIL")
        to_email = os.getenv("HOTEL_GROUP_EMAIL")
        email_password = os.getenv("EMAIL_PASSWORD")

        if not from_email or not to_email or not email_password:
            return "Erreur : Les informations d'authentification ne sont pas complètes."

        subject = f"Confirmation de réservation - {hotel_name}, Chambre {room_number}"
        
        # Generate email content from template
        email_body = BOOKING_EMAIL_TEMPLATE.replace("{{hotel_name}}", hotel_name) \
                                           .replace("{{room_number}}", str(room_number)) \
                                           .replace("{{customer_name}}", customer_name) \
                                           .replace("{{check_in}}", check_in) \
                                           .replace("{{check_out}}", check_out)
        
        msg = MIMEMultipart('related')
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = Header(subject, 'utf-8')

        # Attach HTML content
        msg.attach(MIMEText(email_body, 'html', 'utf-8'))

        # Attach banner image
        banner_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'banner.jpg')
        try:
            with open(banner_path, 'rb') as img:
                mime_image = MIMEImage(img.read())
                mime_image.add_header('Content-ID', '<BookingBanner>')
                msg.attach(mime_image)
        except FileNotFoundError:
            return {"status": "error", "message": "The file banner.jpg was not found."}


        # Send the email
        with smtplib.SMTP('smtp.gmail.com', 587, timeout=60) as server:
            server.starttls()
            server.login(from_email, email_password)
            server.send_message(msg)

        return f"Email envoyé avec succès pour la réservation de {customer_name} dans l'hôtel {hotel_name}!"

    except smtplib.SMTPException as e:
        return f"Erreur SMTP lors de l'envoi de l'email: {str(e)}"
    except Exception as e:
        return f"Erreur lors de l'envoi de l'email: {str(e)}"

Base = declarative_base()


class Hotel(Base):
    __tablename__ = 'hotels'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    area = Column(String, nullable=False)

    # One-to-many relationship with rooms
    rooms = relationship('Room', back_populates='hotel')


class Room(Base):
    __tablename__ = 'rooms'

    id = Column(Integer, primary_key=True)
    room_number = Column(String(10), unique=True, nullable=False)
    room_type = Column(String(50), nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)
    price_per_night = Column(Numeric(10, 2), nullable=False)
    max_guests = Column(Integer, nullable=False)

    hotel_id = Column(Integer, ForeignKey('hotels.id'), nullable=False)
    hotel = relationship('Hotel', back_populates='rooms')

    # One-to-many relationship with bookings
    bookings = relationship('Booking', back_populates='room')


class Customer(Base):
    __tablename__ = 'customers'

    id = Column(Integer, primary_key=True)
    phone_number = Column(String(15), unique=True)
    name = Column(String(100), nullable=False)

    # One-to-many relationship with bookings
    bookings = relationship('Booking', back_populates='customer')


class Booking(Base):
    __tablename__ = 'bookings'

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    check_in_date = Column(Date, nullable=False)
    check_out_date = Column(Date, nullable=False)
    feedback = Column(String)
    room_id = Column(Integer, ForeignKey('rooms.id'), nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    customer = relationship('Customer', back_populates='bookings')
    room = relationship('Room', back_populates='bookings')


DATABASE_URL = "postgresql://agent:booking@localhost:5432/Hotel_db"

# Create engine and session
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def get_session():
    return Session()

def get_available_rooms(
    check_in: date,
    check_out: date,
    area: str,
    room_type: str = None,
    max_guests: int = None
):
    """
    Get available rooms in hotels within a specified area, based on check-in, check-out,
    optional room type, and max guests.
    """
    session = get_session()
    try:
        # Find hotels in the specified area
        hotels = session.query(Hotel).filter(Hotel.area == area).all()
        if not hotels:
            return f"No hotels found in the area '{area}'."

        # Get hotel IDs for querying rooms
        hotel_ids = [hotel.id for hotel in hotels]

        # Query to find rooms in the hotels in the area that are not booked during the given period
        query = session.query(Room).join(Hotel).outerjoin(Booking).filter(
            Room.hotel_id.in_(hotel_ids),
            (Booking.check_in_date >= check_out) | (Booking.check_out_date <= check_in) | (Booking.id == None),
            Room.is_available == True
        )

        # Filter by room type if provided
        if room_type:
            query = query.filter(Room.room_type == room_type)

        # Filter by max guests if provided
        if max_guests:
            query = query.filter(Room.max_guests >= max_guests)

        available_rooms = query.all()

        if not available_rooms:
            return f"No rooms available in the area '{area}' for the selected dates, room type: {room_type}, and max guests: {max_guests}."

        # Group and structure the results by hotel
        result = []
        for room in available_rooms:
            hotel = room.hotel  # Use the relationship to get the hotel directly
            result.append({
                "hotel_name": hotel.name,
                "hotel_area": hotel.area,
                "room_number": room.room_number,
                "room_type": room.room_type,
                "price_per_night": float(room.price_per_night),
                "max_guests": room.max_guests,
            })

        return result
    finally:
        session.close()

def get_customer_by_phone_number(phone_number: str):
    """
    Retrieve a customer's details using their phone number.

    """
    session = get_session()
    try:
        # Query for the customer using the provided phone number
        customer = session.query(Customer).filter(Customer.phone_number == phone_number).first()
        if not customer:
            return f"No customer found with phone number '{phone_number}'."

        # Prepare the customer's data
        result = {
            "customer_id": customer.id,
            "phone_number": customer.phone_number,
            "bookings": [
                {
                    "booking_id": booking.id,
                    "check_in_date": booking.check_in_date,
                    "check_out_date": booking.check_out_date,
                    "room_id": booking.room_id,
                }
                for booking in customer.bookings
            ],
        }
        return result
    finally:
        session.close()
# Add a new customer to the database
def add_customer(phone_number: str, name: str):
    session = get_session()
    try:
        # Check if the customer already exists
        existing_customer = session.query(Customer).filter(Customer.phone_number == phone_number).first()
        if existing_customer:
            return f"Customer with phone number '{phone_number}' already exists."

        # Create and add the new customer
        new_customer = Customer(phone_number=phone_number, name=name)
        session.add(new_customer)
        session.commit()

        return f"Customer '{name}' with phone number '{phone_number}' added successfully."
    except Exception as e:
        session.rollback()
        return f"Error adding customer: {e}"
    finally:
        session.close()
def book_room(
    hotel_name: str,
    room_number: str,
    customer_number: str,
    check_in: date,
    check_out: date
):
    """
    Book a room in a specified hotel for a given period.
    """
    session = get_session()
    try:
        # Find the hotel by name
        hotel = session.query(Hotel).filter(Hotel.name == hotel_name).first()
        if not hotel:
            return f"Hotel '{hotel_name}' does not exist."

        # Find the room in the specified hotel
        room = session.query(Room).filter_by(room_number=room_number, hotel_id=hotel.id).first()
        if not room:
            return f"Room {room_number} does not exist in hotel '{hotel_name}'."

        # Check for overlapping bookings
        overlapping_bookings = session.query(Booking).filter(
            Booking.room_id == room.id,
            Booking.check_in_date < check_out,
            Booking.check_out_date > check_in
        ).all()

        if overlapping_bookings:
            return f"Room {room_number} in hotel '{hotel_name}' is not available from {check_in} to {check_out}."

        # Find or create the customer
        customer = session.query(Customer).filter(Customer.phone_number == customer_number).first()
        if not customer:
            return f"Customer with phone number {customer_number} does not exist. Please register the customer first."

        # Create a new booking
        new_booking = Booking(
            room_id=room.id,
            customer_id=customer.id,
            check_in_date=check_in,
            check_out_date=check_out
        )
        session.add(new_booking)
        session.commit()

        return f"Room {room_number} in hotel '{hotel_name}' successfully booked for {customer.name} ({customer.phone_number}) from {check_in} to {check_out}."
    finally:
        session.close()



# Function to delete a booking
def delete_booking(booking_id: int):
    """
    Delete a booking by its ID.
    """
    session = get_session()
    try:
        # Fetch the booking by its ID
        booking = session.query(Booking).filter_by(id=booking_id).first()
        if not booking:
            return f"Booking with ID {booking_id} does not exist."

        # Delete the booking
        session.delete(booking)
        session.commit()

        return f"Booking with ID {booking_id} has been successfully deleted."
    except Exception as e:
        session.rollback()  # Rollback in case of an error
        return f"An error occurred while trying to delete the booking: {str(e)}"
    finally:
        session.close()

# Function to alter a booking
def alter_booking(
    booking_id: int,
    new_check_in: date = None,
    new_check_out: date = None,
    new_customer_number: str = None,
    new_feedback: str = None
):
    """
    Alter an existing booking by its ID.
    """
    session = get_session()
    try:
        # Fetch the booking by its ID
        booking = session.query(Booking).filter_by(id=booking_id).first()
        if not booking:
            return f"Booking with ID {booking_id} does not exist."

        # Validate date changes for overlapping bookings
        if new_check_in or new_check_out:
            check_in = new_check_in or booking.check_in_date
            check_out = new_check_out or booking.check_out_date

            overlapping_bookings = session.query(Booking).filter(
                Booking.room_id == booking.room_id,
                Booking.id != booking_id,  # Exclude the current booking
                Booking.check_in_date < check_out,
                Booking.check_out_date > check_in
            ).all()

            if overlapping_bookings:
                return f"Updated dates overlap with an existing booking. Please select different dates."

            # Update check-in and check-out dates
            booking.check_in_date = check_in
            booking.check_out_date = check_out

        # Update other fields if new values are provided
        if new_customer_number:
            booking.customer_number = new_customer_number
        if new_feedback:
            booking.feedback = new_feedback

        session.commit()
        return f"Booking with ID {booking_id} has been successfully updated."
    except Exception as e:
        session.rollback()  # Rollback in case of an error
        return f"An error occurred while trying to update the booking: {str(e)}"
    finally:
        session.close()

# Function to find a booking by customer number
def find_booking_by_number(customer_number: str):
    session = Session()
    customer = session.query(Customer).filter_by(phone_number=customer_number).first()
    if customer:
        bookings = session.query(Booking).filter_by(customer_id=customer.id).all()
        return bookings
    return []
# Function to add feedback to a specific booking
def add_feedback(booking_id: int, feedback: str):
    """
    Add or update feedback for a specific booking by its ID.
    """
    session = get_session()
    try:
        booking = session.query(Booking).filter_by(id=booking_id).first()
        if not booking:
            return f"Booking with ID {booking_id} does not exist."

        booking.feedback = feedback
        session.commit()
        return f"Feedback added to booking with ID {booking_id}."
    finally:
        session.close()
# Tool integration for the agent
def chromadb_retrieval(query_embedding):

    client = init_chromadb_client()
    collection_name = "default_collection"  # Update with your collection name
    results = retrieve_info(client, collection_name, query_embedding)
    return results


def hangup():
    response = VoiceResponse()
    response.hangup()
    return response


def main():
    # Insert a customer (if they don't exist yet)
    customer_number = "+212673375314"
    customer_name = "John Doe"

    session = get_session()

    # Check if the customer already exists
    customer = session.query(Customer).filter(Customer.phone_number == customer_number).first()
    if not customer:
        customer = Customer(name=customer_name, phone_number=customer_number)
        session.add(customer)
        session.commit()
        print(f"Customer {customer_name} with phone number {customer_number} added.")
    else:
        print(f"Customer {customer_name} with phone number {customer_number} already exists.")

    # Find available rooms in Casablanca
    area = "Casablanca"
    available_rooms = get_available_rooms(check_in=date(2025, 1, 20), check_out=date(2025, 1, 25), area=area)

    if available_rooms:
        print(f"Available Rooms: {available_rooms}")
    else:
        print(f"No rooms available in the area '{area}'.")

    if available_rooms:
        # Assuming the first available room is booked
        room_to_book = available_rooms[0]  # You can customize this if you need specific logic

        # Extract relevant data from room_to_book
        hotel_name = room_to_book['hotel_name']
        room_number = room_to_book['room_number']
        customer_number = customer.phone_number  # Assuming the customer has already been added and the phone number is available
        check_in = date(2025, 1, 20)  # Customize the check-in date
        check_out = date(2025, 1, 25)  # Customize the check-out date

        # Proceed with booking
        booking_response = book_room(hotel_name, room_number, customer_number, check_in, check_out)
        print(f"Booking Response: {booking_response}")
    else:
        print("No rooms available to book.")

    session.close()



