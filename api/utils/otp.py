import random
import requests
from django.conf import settings

def generate_otp():
    return str(random.randint(100000, 999999))

def send_otp(phone_number, otp):
    """
    Send OTP using Taqnyat SMS API
    """
    url = settings.TAQNYAT_API_URL
    headers = {
        "Authorization": f"Bearer {settings.TAQNYAT_API_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "recipients": [phone_number],
        "body": f"Your OTP is {otp}",
        "sender": settings.TAQNYAT_SENDER_NAME
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        raise Exception(f"Taqnyat SMS failed: {response.text}")

    return response.json()
