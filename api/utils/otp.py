import random
import requests
from django.conf import settings

def generate_otp():
    return str(random.randint(100000, 999999))

def send_otp(phone_number, otp):
    """
    Send OTP using Taqnyat SMS API (HTTP POST style)
    """
    phone_number = phone_number.lstrip('+').replace(" ", "")

    url = f"{settings.TAQNYAT_API_URL}"
    payload = {
        "body": f"Your OTP is {otp}",
        "recipients": [phone_number],  # Must be a list
        "sender": settings.TAQNYAT_SENDER_NAME
    }

    headers = {
        "Authorization": f"Bearer {settings.TAQNYAT_API_TOKEN}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code not in [200, 201]:
        raise Exception(f"Taqnyat SMS failed: {response.text}")

    return response.json()
