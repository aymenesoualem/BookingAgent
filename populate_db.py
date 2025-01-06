import psycopg2
from psycopg2 import sql

# Database connection parameters
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "Hotel_db"
DB_USER = "agent"
DB_PASSWORD = "booking"

def create_and_populate_tables():
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
        room_id INTEGER NOT NULL REFERENCES rooms(id),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    # Sample data to populate the rooms table
    sample_data_query = """
    INSERT INTO rooms (room_number, room_type, is_available, price_per_night, max_guests)
    VALUES
        ('101', 'Single', TRUE, 50.00, 1),
        ('102', 'Double', TRUE, 75.00, 2),
        ('103', 'Suite', TRUE, 120.00, 4),
        ('104', 'Single', TRUE, 50.00, 1),
        ('105', 'Double', TRUE, 75.00, 2)
    ON CONFLICT (room_number) DO NOTHING;
    """

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

        # Execute table creation and data insertion
        print("Creating tables...")
        cursor.execute(create_table_query)
        print("Tables created successfully.")

        print("Inserting sample data into rooms table...")
        cursor.execute(sample_data_query)
        print("Sample data inserted successfully.")

    except psycopg2.Error as e:
        print("Error while interacting with PostgreSQL:", e)
    finally:
        # Close the cursor and connection
        if cursor:
            cursor.close()
        if connection:
            connection.close()
        print("PostgreSQL connection closed.")

if __name__ == "__main__":
    create_and_populate_tables()
