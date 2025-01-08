from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey, Numeric, Boolean, TIMESTAMP, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import date

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

# ###Uncomment to test code
# if __name__ == "__main__":
#     from datetime import datetime
#
#     # Input for hotel details
#     hotel_name = input("Enter the hotel name: ").strip()
#     room_type = input("Enter the desired room type (or leave blank for any): ").strip()
#     max_guests = input("Enter the maximum number of guests (or leave blank for any): ").strip()
#
#     # Parse max_guests input
#     max_guests = int(max_guests) if max_guests.isdigit() else None
#
#     # Input for booking dates
#     check_in_date = input("Enter check-in date (YYYY-MM-DD): ").strip()
#     check_out_date = input("Enter check-out date (YYYY-MM-DD): ").strip()
#
#     try:
#         # Convert input dates to `date` objects
#         check_in = datetime.strptime(check_in_date, "%Y-%m-%d").date()
#         check_out = datetime.strptime(check_out_date, "%Y-%m-%d").date()
#
#         # Ensure the dates are valid
#         if check_in >= check_out:
#             print("Check-out date must be after check-in date.")
#         else:
#             # Get available rooms
#             available_rooms = get_available_rooms(
#                 check_in, check_out, hotel_name, room_type if room_type else None, max_guests
#             )
#
#             if isinstance(available_rooms, str):
#                 # No rooms available
#                 print(available_rooms)
#             else:
#                 # Display available rooms
#                 print("Available rooms:")
#                 for room in available_rooms:
#                     print(
#                         f"Room {room['room_number']} - Type: {room['room_type']}, "
#                         f"Price per night: {room['price_per_night']}, Max Guests: {room['max_guests']}"
#                     )
#
#                 # Ask if the user wants to book a room
#                 book_choice = input("Do you want to book a room? (yes/no): ").strip().lower()
#                 if book_choice == "yes":
#                     room_number = input("Enter the room number to book: ").strip()
#                     customer_name = input("Enter your name: ").strip()
#
#                     # Attempt to book the room
#                     booking_response = book_room(hotel_name, room_number, customer_name, check_in, check_out)
#                     print(booking_response)
#
#     except ValueError:
#         print("Invalid date format. Please enter dates in YYYY-MM-DD format.")
