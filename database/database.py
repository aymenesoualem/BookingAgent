import psycopg2
from psycopg2 import sql
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

    CREATE TABLE IF NOT EXISTS bookings (
        id SERIAL PRIMARY KEY,
        customer_name VARCHAR(100) NOT NULL,
        check_in_date DATE NOT NULL,
        check_out_date DATE NOT NULL,
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
        ('101', 'Single', True, 60.00, 1, 1),
        ('102', 'Double', True, 100.00, 2, 1),
        ('103', 'Suite', True, 180.00, 4, 1),

        # Rooms for Hotel Saadien
        ('201', 'Single', True, 65.00, 1, 2),
        ('202', 'Double', True, 110.00, 2, 2),
        ('203', 'Suite', True, 190.00, 4, 2),

        # Rooms for Hotel Imperial
        ('301', 'Single', True, 55.00, 1, 3),
        ('302', 'Double', True, 90.00, 2, 3),
        ('303', 'Suite', True, 170.00, 4, 3),

        # Rooms for Hotel Medina
        ('401', 'Single', True, 70.00, 1, 4),
        ('402', 'Double', True, 120.00, 2, 4),
        ('403', 'Suite', True, 200.00, 4, 4),

        # Rooms for Hotel Oasis
        ('501', 'Single', True, 50.00, 1, 5),
        ('502', 'Double', True, 85.00, 2, 5),
        ('503', 'Suite', True, 150.00, 4, 5),

        # Rooms for Hotel Al-Bahr
        ('601', 'Single', True, 75.00, 1, 6),
        ('602', 'Double', True, 130.00, 2, 6),
        ('603', 'Suite', True, 220.00, 4, 6),
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
