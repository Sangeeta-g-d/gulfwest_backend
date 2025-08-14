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

def send_otp(phone_number, otp):
    """
    Send OTP using Taqnyat SMS API (HTTP POST style) with debug logging
    """
    logger.debug(f"Raw phone number input: {phone_number}")

    phone_number = phone_number.lstrip('+').replace(" ", "")
    logger.debug(f"Processed phone number: {phone_number}")

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

    logger.debug(f"Sending POST request to {url}")
    logger.debug(f"Payload: {payload}")
    logger.debug(f"Headers: {headers}")

    try:
        response = requests.post(url, json=payload, headers=headers)
        logger.debug(f"Response status code: {response.status_code}")
        logger.debug(f"Response text: {response.text}")

        if response.status_code not in [200, 201]:
            logger.error(f"Taqnyat SMS failed: {response.text}")
            raise Exception(f"Taqnyat SMS failed: {response.text}")

        logger.info(f"OTP sent successfully to {phone_number}")
        return response.json()

    except Exception as e:
        logger.exception(f"Error while sending OTP to {phone_number}: {e}")
        raise
