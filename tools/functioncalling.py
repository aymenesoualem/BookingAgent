import inspect
import os
from datetime import date

from tools import send_sms, send_email_with_banner, book_room, get_available_rooms, web_scraper_for_recommendation
from tools.tools import delete_booking, alter_booking, find_booking_by_number, add_feedback


def book_room_function(hotel_name: str, room_number: str, customer_name: str,customer_number: str, check_in: date, check_out: date):
    """This function books a room, call this function when the user wants to book a room."""

    # Book the room (you can add your room booking logic here)
    # Here we assume the room is successfully booked
    booking_details = f"Booking Confirmation:\nHotel: {hotel_name}\nRoom Number: {room_number}\nCustomer: {customer_name}\nCheck-in: {check_in}\nCheck-out: {check_out}"

    # Send the booking confirmation to the hotel
    hotel_phone_number = os.getenv('HOTEL_PHONE_NUMBER')  # The hotel's phone number should be set as an environment variable
    confirmation_message = f"Room booked successfully!\n{booking_details}"

    # Send confirmation SMS to the hotel
    send_sms(hotel_phone_number, confirmation_message)
    send_email_with_banner(hotel_name,room_number, customer_name, check_in, check_out)
    return book_room(hotel_name, room_number, customer_name,customer_number, check_in, check_out)

def get_available_rooms_function(
    check_in: date,
    check_out: date,
    area: str,
    room_type: str = None,
    max_guests: int = None
):
    """Fetches available rooms in a specified area for given check-in and check-out dates. Optionally filters by room type and maximum guest count."""
    return get_available_rooms(check_in, check_out, area, room_type, max_guests)
def delete_booking_function(booking_id: int):
    """
    Deletes a booking record using the booking ID.
    """
    return delete_booking(booking_id)

def alter_booking_function(
    booking_id: int,
    new_check_in: date = None,
    new_check_out: date = None,
    new_customer_name: str = None,
    new_customer_number: str = None,
):
    """
    Modifies an existing booking with updated details such as dates or customer information.
    """
    return alter_booking(booking_id, new_check_in, new_check_out, new_customer_name, new_customer_number)

def find_booking_by_number_function(customer_number: str):
    """
    Searches for a booking using the customer's phone number.
    """
    return find_booking_by_number(customer_number)

def add_feedback_function(booking_id: int, feedback: str):
    """
    Adds feedback for a specific booking.
    """
    return add_feedback(booking_id, feedback)

def webscraper_for_recommendations_function(topic:str):
    """Fetches for things to do in the hotels area, uae this function when the user asks for things to do while visiting the hotel's area."""
    return web_scraper_for_recommendation(topic)

def function_to_schema(func) -> dict:
    """
    Converts a Python function's signature into a JSON schema format.

    Args:
        func: The Python function to convert into a JSON schema.

    Returns:
        dict: A JSON schema describing the function.
    """
    # Map Python types to JSON Schema types
    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
        type(None): "null",
        date: "string",  # Represent date as a string in ISO 8601 format
    }

    try:
        signature = inspect.signature(func)
    except ValueError:
        raise ValueError(f"Failed to get signature for function {func.__name__}.")

    # Extract parameter properties
    properties = {}
    required = []
    for param in signature.parameters.values():
        annotation = param.annotation
        param_type = type_map.get(annotation, "string")  # Default to "string" if unknown
        properties[param.name] = {"type": param_type}

        # Add a format for date type
        if annotation == date:
            properties[param.name]["format"] = "date"

        # Add to required list if no default value is provided
        if param.default is inspect.Parameter.empty:
            required.append(param.name)

    return {
        "type": "function",
        "name": func.__name__,
        "description": (func.__doc__ or "").strip(),
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
    }




async def invoke_function(function_name, arguments):
    """
    Dynamically invokes a function by name with the given arguments.
    """
    try:
        # Map function names to actual functions
        function_map = {
            "get_available_rooms_function": get_available_rooms_function,
            "book_room_function": book_room_function,
            "webscraper_for_recommendations_function": webscraper_for_recommendations_function,
            # Add more functions here as needed
        }
        if function_name in function_map:
            result = function_map[function_name](**arguments)
            print(f"Function {function_name} invoked successfully with result: {result}")
            return result
        else:
            print(f"Function {function_name} is not recognized.")
    except Exception as e:
        print(f"Error invoking function {function_name}: {e}")
