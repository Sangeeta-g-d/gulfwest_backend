import random
import requests
import logging
from django.conf import settings

# Configure logger
logger = logging.getLogger(__name__)

def generate_otp():
    otp = str(random.randint(100000, 999999))
    logger.debug(f"Generated OTP: {otp}")
    return otp

def otp_to_words(otp: str) -> str:
    """
    Convert numeric OTP into words (e.g. "1234" -> "one two three four")
    """
    digit_map = {
        "0": "zero",
        "1": "one",
        "2": "two",
        "3": "three",
        "4": "four",
        "5": "five",
        "6": "six",
        "7": "seven",
        "8": "eight",
        "9": "nine",
    }
    return " ".join(digit_map[d] for d in otp)


def send_otp_sms_template(phone_number, otp):
    phone_number = phone_number.lstrip('+').replace(" ", "")

    url = settings.TAQNYAT_API_URL.rstrip('/') + "/messagesVars"
    payload = {
        "sender": settings.TAQNYAT_SENDER_NAME,
        "body": "Your OTP is CodeVar",   # Template with variable
        "recipients": [phone_number],
        "vars": [
            {"CodeVar": otp}
        ]
    }

    headers = {
        "Authorization": f"Bearer {settings.TAQNYAT_API_TOKEN}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code not in [200, 201]:
        logger.error(f"SMS Template failed: {response.text}")
        raise Exception(f"SMS Template failed: {response.text}")

    logger.info(f"OTP SMS sent successfully to {phone_number}")
    return response.json()
