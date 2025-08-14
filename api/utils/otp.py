import random
import requests
from django.conf import settings

def generate_otp():
    """Generate a random 6-digit OTP."""
    return str(random.randint(100000, 999999))

def format_phone_for_taqnyat(phone_number: str) -> str:
    """
    Format phone number to Taqnyat's expected format:
    - No '+' or '00'
    - Full country code + number
    - No spaces or dashes
    """
    phone_number = phone_number.strip().replace(" ", "").replace("-", "")
    if phone_number.startswith("+"):
        phone_number = phone_number[1:]
    if phone_number.startswith("00"):
        phone_number = phone_number[2:]
    return phone_number

def send_otp(phone_number, otp):
    """Send OTP using Taqnyat SMS API (HTTP POST)."""
    formatted_phone = format_phone_for_taqnyat(phone_number)

    url = settings.TAQNYAT_API_URL
    payload = {
        "body": f"Your OTP is {otp}",
        "recipients": [formatted_phone],  # Must be a list
        "sender": settings.TAQNYAT_SENDER_NAME
    }

    headers = {
        "Authorization": f"Bearer {settings.TAQNYAT_API_TOKEN}",
        "Content-Type": "application/json"
    }

    print("=== DEBUG: Sending OTP ===")
    print("URL:", url)
    print("Payload:", payload)
    print("Headers:", headers)

    response = requests.post(url, json=payload, headers=headers)

    print("=== DEBUG: Response Status:", response.status_code)
    print("=== DEBUG: Response Body:", response.text)

    if response.status_code not in [200, 201]:
        raise Exception(f"Taqnyat SMS failed: {response.text}")

    return response.json()
