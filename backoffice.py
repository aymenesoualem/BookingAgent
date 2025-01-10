import asyncio

import streamlit as st
import requests
import pandas as pd

from outboundcall import make_call


# Function to fetch bookings from the API
def fetch_bookings():
    try:
        url = "https://actually-liked-doe.ngrok-free.app/bookings"  # Replace with your API URL
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data: {e}")
        return []


# Main Streamlit App
def main():
    st.set_page_config(page_title="Booking Management", layout="wide")
    st.title("Booking Management")

    # Fetch data on app startup
    bookings = fetch_bookings()

    if bookings:
        # Convert bookings to a DataFrame for better display
        df = pd.DataFrame(bookings)

        if not df.empty:
            st.subheader("Bookings Data")
            for _, row in df.iterrows():
                # Create columns to layout booking details and the button
                col1, col2, col3,col4 = st.columns([2, 4, 2,4])

                with col1:
                    st.write(f"**Booking ID**: {row.get('id', 'N/A')}")
                    st.write(f"**Customer Name**: {row.get('customer_name', 'N/A')}")

                with col2:
                    st.write(f"**Phone Number**: {row.get('phone_number', 'N/A')}")
                with col3:
                    st.write(f"**Customer Feedack**: {row.get('feedback', 'N/A')}")

                with col4:
                    phone_number = row.get('phone_number', 'N/A')
                    if phone_number != 'N/A':  # Ensure a valid phone number exists
                        if st.button(f"Call {phone_number}", key=phone_number):
                            with st.spinner(f"Initiating call to {phone_number}..."):
                                try:
                                    asyncio.run(make_call(phone_number))
                                    st.success(f"Call successfully initiated to {phone_number}")
                                except Exception as e:
                                    st.error(f"Error initiating call to {phone_number}: {str(e)}")
                    else:
                        st.warning("No valid phone number to call.")

                st.markdown("---")
        else:
            st.warning("No bookings found.")
    else:
        st.warning("Could not retrieve bookings data.")



if __name__ == "__main__":
    main()
