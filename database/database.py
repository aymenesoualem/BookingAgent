import psycopg2
from psycopg2.errors import DuplicateTable, UniqueViolation

# Database connection parameters
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "Hotel_db"
DB_USER = "agent"
DB_PASSWORD = "booking"

def create_tables():
    # SQL commands to drop and create tables
    create_table_query = """
    DROP TABLE IF EXISTS bookings CASCADE;
    DROP TABLE IF EXISTS rooms CASCADE;
    DROP TABLE IF EXISTS hotels CASCADE;
    DROP TABLE IF EXISTS customers CASCADE;

    CREATE TABLE IF NOT EXISTS hotels (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL UNIQUE,
        area VARCHAR(100) NOT NULL
    );

    CREATE TABLE IF NOT EXISTS rooms (
        id SERIAL PRIMARY KEY,
        room_number VARCHAR(10) NOT NULL UNIQUE,
        room_type VARCHAR(50) NOT NULL,
        is_available BOOLEAN NOT NULL DEFAULT TRUE,
        price_per_night NUMERIC(10, 2) NOT NULL,
        max_guests INTEGER NOT NULL,
        hotel_id INTEGER NOT NULL REFERENCES hotels(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS customers (
        id SERIAL PRIMARY KEY,
        phone_number VARCHAR(15) UNIQUE,
        name VARCHAR(100) NOT NULL
    );

    CREATE TABLE IF NOT EXISTS bookings (
        id SERIAL PRIMARY KEY,
        customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
        check_in_date DATE NOT NULL,
        check_out_date DATE NOT NULL,
        feedback TEXT,
        room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    return create_table_query

def populate_hotels():
    # Parameterized sample data query for hotels
    sample_hotels_query = """
    INSERT INTO hotels (name, area)
    VALUES (%s, %s)
    ON CONFLICT (name) DO NOTHING;
    """
    sample_hotels = [
        ("Hotel Atlas", "Marrakech"),
        ("Hotel Saadien", "Casablanca"),
        ("Hotel Imperial", "Fez"),
        ("Hotel Medina", "Rabat"),
        ("Hotel Oasis", "Agadir"),
        ("Hotel Al-Bahr", "Tangier")
    ]
    return sample_hotels_query, sample_hotels

def populate_rooms():
    # Parameterized sample data query for rooms
    sample_rooms_query = """
    INSERT INTO rooms (room_number, room_type, is_available, price_per_night, max_guests, hotel_id)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (room_number) DO NOTHING;
    """
    sample_rooms = [
        # Rooms for Hotel Atlas
        ('1011', 'Single', True, 60.00, 1, 1),
        ('1012', 'Double', True, 100.00, 2, 1),
        ('1031', 'Suite', True, 180.00, 4, 1),
        ('1041', 'Deluxe', True, 250.00, 5, 1),
        ('111', 'Single', True, 60.00, 1, 1),
        ('012', 'Double', True, 100.00, 2, 1),
        ('031', 'Suite', True, 180.00, 4, 1),
        ('141', 'Deluxe', True, 250.00, 5, 1),

        # Rooms for Hotel Saadien
        ('2011', 'Single', True, 65.00, 1, 2),
        ('2021', 'Double', True, 110.00, 2, 2),
        ('2031', 'Suite', True, 190.00, 4, 2),
        ('2041', 'Deluxe', True, 240.00, 5, 2),
        ('211', 'Single', True, 65.00, 1, 2),
        ('221', 'Double', True, 110.00, 2, 2),
        ('231', 'Suite', True, 190.00, 4, 2),
        ('241', 'Deluxe', True, 240.00, 5, 2),

        # Rooms for Hotel Imperial
        ('3011', 'Single', True, 55.00, 1, 3),
        ('3021', 'Double', True, 90.00, 2, 3),
        ('3031', 'Suite', True, 170.00, 4, 3),
        ('3041', 'Deluxe', True, 230.00, 5, 3),
        ('311', 'Single', True, 55.00, 1, 3),
        ('321', 'Double', True, 90.00, 2, 3),
        ('331', 'Suite', True, 170.00, 4, 3),
        ('341', 'Deluxe', True, 230.00, 5, 3),

        # Rooms for Hotel Medina
        ('411', 'Single', True, 70.00, 1, 4),
        ('421', 'Double', True, 120.00, 2, 4),
        ('431', 'Suite', True, 200.00, 4, 4),
        ('441', 'Deluxe', True, 280.00, 5, 4),

        # Rooms for Hotel Oasis
        ('511', 'Single', True, 50.00, 1, 5),
        ('521', 'Double', True, 85.00, 2, 5),
        ('531', 'Suite', True, 150.00, 4, 5),
        ('541', 'Deluxe', True, 220.00, 5, 5),

        # Rooms for Hotel Al-Bahr
        ('611', 'Single', True, 75.00, 1, 6),
        ('621', 'Double', True, 130.00, 2, 6),
        ('631', 'Suite', True, 220.00, 4, 6),
        ('641', 'Deluxe', True, 300.00, 5, 6),
        # Rooms for Hotel Medina
        ('4011', 'Single', True, 70.00, 1, 4),
        ('4021', 'Double', True, 120.00, 2, 4),
        ('4031', 'Suite', True, 200.00, 4, 4),
        ('4041', 'Deluxe', True, 280.00, 5, 4),

        # Rooms for Hotel Oasis
        ('5011', 'Single', True, 50.00, 1, 5),
        ('5021', 'Double', True, 85.00, 2, 5),
        ('5031', 'Suite', True, 150.00, 4, 5),
        ('5041', 'Deluxe', True, 220.00, 5, 5),

        # Rooms for Hotel Al-Bahr
        ('6011', 'Single', True, 75.00, 1, 6),
        ('6021', 'Double', True, 130.00, 2, 6),
        ('6031', 'Suite', True, 220.00, 4, 6),
        ('6041', 'Deluxe', True, 300.00, 5, 6),
    ]
    return sample_rooms_query, sample_rooms


def create_and_populate_tables():
    try:
        # Connect to PostgreSQL
        connection = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        connection.autocommit = True
        cursor = connection.cursor()

        # Execute table creation
        print("Creating tables...")
        cursor.execute(create_tables())
        print("Tables created successfully.")

        # Insert sample hotels data
        print("Inserting sample data into hotels table...")
        hotel_query, hotels_data = populate_hotels()
        cursor.executemany(hotel_query, hotels_data)
        print("Hotels data inserted successfully.")

        # Insert sample rooms data
        print("Inserting sample data into rooms table...")
        room_query, rooms_data = populate_rooms()
        cursor.executemany(room_query, rooms_data)
        print("Rooms data inserted successfully.")

        # Insert sample bookings data
        print("Inserting sample data into bookings table...")
        booking_query, bookings_data = populate_rooms()
        cursor.executemany(booking_query, bookings_data)
        print("Bookings data inserted successfully.")

    except DuplicateTable as dt_err:
        print("Table already exists:", dt_err)
    except UniqueViolation as uv_err:
        print("Duplicate entry error:", uv_err)
    except psycopg2.Error as e:
        print("Error while interacting with PostgreSQL:", e)
    finally:
        # Close the cursor and connection
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'connection' in locals() and connection:
            connection.close()
        print("PostgreSQL connection closed.")

if __name__ == "__main__":
    create_and_populate_tables()
