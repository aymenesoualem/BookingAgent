from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey, Numeric, Boolean, TIMESTAMP, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import date

Base = declarative_base()

class Room(Base):
    __tablename__ = 'rooms'
    id = Column(Integer, primary_key=True)
    room_number = Column(String(10), unique=True, nullable=False)
    room_type = Column(String(50), nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)
    price_per_night = Column(Numeric(10, 2), nullable=False)
    max_guests = Column(Integer, nullable=False)

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

def book_room(room_number: str, customer_name: str, check_in: date, check_out: date):
    session = get_session()
    try:
        room = session.query(Room).filter_by(room_number=room_number).first()
        if not room:
            return f"Room {room_number} does not exist."

        # Check for overlapping bookings
        overlapping_bookings = session.query(Booking).filter(
            Booking.room_id == room.id,
            Booking.check_in_date < check_out,
            Booking.check_out_date > check_in
        ).all()

        if overlapping_bookings:
            return f"Room {room_number} is not available from {check_in} to {check_out}."

        # Create a new booking
        new_booking = Booking(
            room_id=room.id,
            customer_name=customer_name,
            check_in_date=check_in,
            check_out_date=check_out
        )
        session.add(new_booking)
        session.commit()

        return f"Room {room_number} successfully booked for {customer_name} from {check_in} to {check_out}."
    finally:
        session.close()


def get_available_rooms(check_in: date, check_out: date):
    session = get_session()
    try:
        # Subquery to find rooms that are booked during the given period
        subquery = session.query(Booking.room_id).filter(
            Booking.check_in_date < check_out,
            Booking.check_out_date > check_in
        ).subquery()

        # Query to find rooms not in the subquery and are available
        available_rooms = session.query(Room).filter(
            Room.id.notin_(subquery), Room.is_available == True
        ).all()

        if not available_rooms:
            return "No rooms available for the selected dates."

        return [room.room_number for room in available_rooms]
    finally:
        session.close()

# ####Uncomment to test the  code
# if __name__ == "__main__":
#     # Test booking a room
#     print(book_room('101', 'John Doe', date(2025, 1, 10), date(2025, 1, 15)))
#
#     # Get available rooms
#     available_rooms = get_available_rooms(date(2025, 1, 10), date(2025, 1, 15))
#     print("Available rooms:", available_rooms)
