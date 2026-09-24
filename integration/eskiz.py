from eskiz_sms import EskizSMS
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class EskizOTP():
    @staticmethod
    def send_otp_service(phone_number, message):
        try:
            email = os.getenv("ESKIZ_EMAIL")
            password = os.getenv("ESKIZ_PASSWORD")
            eskiz = EskizSMS(email=email, password=password)
            eskiz.send_sms(phone_number, message, from_whom='4546', callback_url=None)
        except Exception as e:
            logger.error(f"Failed to send SMS via Eskiz to {phone_number}: {e}")
        
