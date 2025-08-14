import random
import requests
from django.conf import settings

def generate_otp():
    return str(random.randint(100000, 999999))

def send_otp(phone_number, otp):
    """
    Send OTP using Taqnyat SMS API (HTTP POST style)
    """
    print("=== DEBUG: Raw input phone number:", phone_number)
    phone_number = phone_number.lstrip('+').replace(" ", "")
    print("=== DEBUG: Cleaned phone number:", phone_number)
    print("=== DEBUG: Generated OTP:", otp)

    url = f"{settings.TAQNYAT_API_URL}"
    payload = {
        "body": f"Your OTP is {otp}",
        "recipients": [phone_number],  # Must be a list
        "sender": settings.TAQNYAT_SENDER_NAME
    }
    print("=== DEBUG: API URL:", url)
    print("=== DEBUG: Request payload:", payload)

    headers = {
        "Authorization": f"Bearer {settings.TAQNYAT_API_TOKEN}",
        "Content-Type": "application/json"
    }
    print("=== DEBUG: Request headers:", headers)

    response = requests.post(url, json=payload, headers=headers)

    print("=== DEBUG: Response status code:", response.status_code)
    print("=== DEBUG: Response body:", response.text)

    if response.status_code not in [200, 201]:
        raise Exception(f"Taqnyat SMS failed: {response.text}")

    return response.json()
