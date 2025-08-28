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
def send_otp(phone_number, otp):
    """
    Send OTP using Taqnyat SMS API (HTTP POST style) with debug logging.
    Sends bilingual message (English + Arabic) with numeric + word format.
    """
    logger.debug(f"Raw phone number input: {phone_number}")

    phone_number = phone_number.lstrip('+').replace(" ", "")
    logger.debug(f"Processed phone number: {phone_number}")

    url = settings.TAQNYAT_API_URL.rstrip('/') + "/v1/messages"

    # Convert OTP digits to words
    otp_in_words = otp_to_words(otp)

    # Bilingual OTP message with number + words
    message_body = (
        f"HALA WALLA!!\n"
        f"Your one type password is: {otp} ({otp_in_words}), Never share this code with anyone\n"
        f"gulfwest.com\n\n"
        f"هلا و الله !!!\n"
        f"رمز التأكيد الخاص بك {otp} ({otp_in_words}), لا تشارك هذا الرمز مع أحد\n"
        f"شركة الخليج الغربية"
    )

    payload = {
        "body": message_body,
        "recipients": [phone_number],
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
