from datetime import datetime, timedelta

from django.conf import settings

from exceptions.error_exception import CustomApiException
from exceptions.error_messages import ErrorCodes
from .models import OTP
from .utils import otp_code_generator


def check_otp_limit(customer):
    """Max 3 SMS OTPs per 12 hours (Telegram OTPs are free and limited separately)."""
    # TODO: temporarily disabled — remove this return to re-enable the SMS OTP limit
    return
    all_otp = OTP.objects.filter(customer_id=customer.id, channel=OTP.Channel.SMS)
    last_otp = all_otp.order_by("-created_at").first()
    if all_otp.count() >= 3 and last_otp.created_at > datetime.now() - timedelta(hours=12):
        raise CustomApiException(error_code=ErrorCodes.ATTEMPT_ALREADY_EXISTS,
                                 time=last_otp.created_at + timedelta(hours=12))


def create_otp(customer, resend=False, check_limit=True, channel=OTP.Channel.SMS):
    """Create a new OTP (expires in 1 minute); older OTPs are cleaned up once the 12-hour window has passed."""
    if check_limit:
        check_otp_limit(customer)

    otp = OTP.objects.create(customer_id=customer.id, otp_code=otp_code_generator(), resend=resend,
                             channel=channel)
    otp.expire_at = otp.created_at + timedelta(seconds=settings.OTP_LIFETIME_SECONDS)
    otp.save(update_fields=["expire_at"])

    all_otp = OTP.objects.filter(customer_id=customer.id)
    latest_otp = all_otp.order_by("-created_at").exclude(otp_key=otp.otp_key).first()
    if latest_otp and latest_otp.created_at < datetime.now() - timedelta(hours=12) and all_otp.count() >= 2:
        all_otp.exclude(otp_key=otp.otp_key).delete()
    return otp
