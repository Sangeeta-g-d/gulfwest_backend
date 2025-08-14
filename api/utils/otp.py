import random
import requests
from django.conf import settings

def generate_otp():
    return str(random.randint(100000, 999999))

def send_otp(phone_number, otp):
    """
    Send OTP using Taqnyat SMS API (HTTP GET style as per documentation)
    """
    phone_number = phone_number.lstrip('+').replace(" ", "")  # Remove + and spaces

    url = f"{settings.TAQNYAT_API_URL}/messages"
    params = {
        "bearerTokens": settings.TAQNYAT_API_TOKEN,
        "sender": settings.TAQNYAT_SENDER_NAME,
        "recipients": phone_number,  # Comma-separated if multiple numbers
        "body": f"Your OTP is {otp}"
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        raise Exception(f"Taqnyat SMS failed: {response.text}")

    return response.json()
