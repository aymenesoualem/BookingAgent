import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.header import Header
from dotenv import load_dotenv
from email_template import BOOKING_EMAIL_TEMPLATE

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
            with open('./assets/banner.jpg', 'rb') as img:
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
