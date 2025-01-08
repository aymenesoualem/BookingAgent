import os

from dotenv import load_dotenv
from tavily import TavilyClient
from twilio.rest import Client

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