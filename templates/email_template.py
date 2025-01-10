import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BOOKING_EMAIL_TEMPLATE = """ 

<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Nouvelle Réservation</title>
<style>
    body {
        font-family: Arial, sans-serif;
        font-size: 16px;
        margin: 0;
        padding: 0;
        color: #333;
        background-color: #f4f4f4;
    }
    .email-container {
        width: 90%;
        max-width: 600px;
        margin: 0 auto;
        padding: 20px;
        background-color: #ffffff;
        border: 1px solid #ddd;
        border-radius: 5px;
        box-shadow: 0 0 10px rgba(0,0,0,0.1);
    }
    .banner-image {
        width: 100%;
        max-width: 600px;
        height: auto;
        display: block;
        margin: 0 auto 20px;
    }
    h2 {
        text-align: center;
        color: #0073AA;
    }
    .booking-details {
        margin-top: 20px;
        padding: 15px;
        background-color: #f9f9f9;
        border: 1px solid #ddd;
        border-radius: 5px;
        line-height: 1.8;
    }
    .booking-details p {
        margin: 10px 0;
        color: #666;
    }
    .footer {
        text-align: center;
        margin-top: 30px;
        padding-top: 20px;
        border-top: 1px solid #ddd;
        font-size: 14px;
    }
    .footer p {
        margin: 0;
        color: #666;
    }
</style>
</head>
<body>
<div class="email-container">
    <img src="cid:BookingBanner" alt="Hotel Group Banner" class="banner-image">
    <h2>&#x2705; Nouvelle Réservation Confirmée &#x2705;</h2>

    <p>Bonjour, une nouvelle réservation a été effectuée. Voici les détails :</p>

    <div class="booking-details">
        <p><span>&#x1F3E8;</span><strong> Hôtel :</strong> {{hotel_name}}</p>
        <p><span>&#x1F511;</span><strong> Numéro de chambre :</strong> {{room_number}}</p>
        <p><span>&#x1F464;</span><strong> Client :</strong> {{customer_name}}</p>
        <p><span>&#x1F4C5;</span><strong> Date d'arrivée :</strong> {{check_in}}</p>
        <p><span>&#x1F4C5;</span><strong> Date de départ :</strong> {{check_out}}</p>
    </div>

    <p>Merci de préparer la chambre pour l'arrivée du client.</p>

    <div class="footer">
        <p>&copy; 2025 Groupe MORAVELO. Tous droits réservés.</p>
    </div>
</div>
</body>
</html>

"""
