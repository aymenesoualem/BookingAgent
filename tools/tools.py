import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.header import Header
from templates.email_template import BOOKING_EMAIL_TEMPLATE
from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey, Numeric, Boolean, TIMESTAMP, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import sys
from datetime import date
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
        try:
            with open('../assets/banner.jpg', 'rb') as img:
                mime_image = MIMEImage(img.read())
                mime_image.add_header('Content-ID', '<BookingBanner>')
                msg.attach(mime_image)
        except FileNotFoundError:
            return "Erreur : Le fichier banner.jpg est introuvable."

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
    name = Column(String(100), unique=True, nullable=False)
    area = Column(String(100), nullable=False)
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

class Booking(Base):
    __tablename__ = 'bookings'
    id = Column(Integer, primary_key=True)
    customer_name = Column(String(100), nullable=False)
    check_in_date = Column(Date, nullable=False)
    check_out_date = Column(Date, nullable=False)
    room_id = Column(Integer, ForeignKey('rooms.id'), nullable=False)
    created_at = Column(TIMESTAMP, default=func.now())
    room = relationship('Room')

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

        # Subquery to find rooms booked during the given period
        subquery = session.query(Booking.room_id).filter(
            Booking.check_in_date < check_out,
            Booking.check_out_date > check_in
        ).subquery()

        # Query to find rooms in the hotels in the area that are not in the subquery and are available
        query = session.query(Room).filter(
            Room.hotel_id.in_(hotel_ids),
            Room.id.notin_(subquery),
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

        # Return room details grouped by hotel
        result = {}
        for room in available_rooms:
            hotel_name = session.query(Hotel.name).filter(Hotel.id == room.hotel_id).scalar()
            if hotel_name not in result:
                result[hotel_name] = []
            result[hotel_name].append({
                "room_number": room.room_number,
                "room_type": room.room_type,
                "price_per_night": float(room.price_per_night),
                "max_guests": room.max_guests,
            })

        return result
    finally:
        session.close()



def book_room(hotel_name: str, room_number: str, customer_name: str, check_in: date, check_out: date):
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

        # Create a new booking
        new_booking = Booking(
            room_id=room.id,
            customer_name=customer_name,
            check_in_date=check_in,
            check_out_date=check_out
        )
        session.add(new_booking)
        session.commit()

        return f"Room {room_number} in hotel '{hotel_name}' successfully booked for {customer_name} from {check_in} to {check_out}."
    finally:
        session.close()