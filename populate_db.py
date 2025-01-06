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
    # SQL commands to create the tables
    create_table_query = """
    CREATE TABLE IF NOT EXISTS rooms (
        id SERIAL PRIMARY KEY,
        room_number VARCHAR(10) NOT NULL UNIQUE,
        room_type VARCHAR(50) NOT NULL,
        is_available BOOLEAN NOT NULL DEFAULT TRUE,
        price_per_night NUMERIC(10, 2) NOT NULL,
        max_guests INTEGER NOT NULL
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

def populate_sample_data():
    # Parameterized sample data query
    sample_data_query = """
    INSERT INTO rooms (room_number, room_type, is_available, price_per_night, max_guests)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (room_number) DO NOTHING;
    """
    sample_data = [
        ('101', 'Single', True, 50.00, 1),
        ('102', 'Double', True, 75.00, 2),
        ('103', 'Suite', True, 120.00, 4),
        ('104', 'Single', True, 50.00, 1),
        ('105', 'Double', True, 75.00, 2)
    ]
    return sample_data_query, sample_data

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

        # Insert sample data
        print("Inserting sample data into rooms table...")
        query, data = populate_sample_data()
        cursor.executemany(query, data)
        print("Sample data inserted successfully.")

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
