from eskiz_sms import EskizSMS
import os
from dotenv import load_dotenv

load_dotenv()


class EskizOTP():
    @staticmethod
    def send_otp_service(phone_number, message):
        email = os.getenv("ESKIZ_EMAIL")
        password = os.getenv("ESKIZ_PASSWORD")
        eskiz = EskizSMS(email=email, password=password)
        eskiz.send_sms(phone_number, message, from_whom='4546', callback_url=None)
        
