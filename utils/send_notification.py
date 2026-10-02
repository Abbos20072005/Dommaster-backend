import os
import logging

import requests
from django.conf import settings
from pyfcm import FCMNotification
from pyfcm.errors import FCMNotRegisteredError
from apps.authorization.models import FcmToken

logger = logging.getLogger(__name__)

def send_notification(message: str) -> None:
    try:
        response = requests.get(settings.TELEGRAM_API_URL + message)
        logger.info("Telegram notification sent: %s", response.text)
    except Exception as e:
        logger.error(f"Failed while sending request to telegram client: {e}")



def push_notification(message_title: str, message_body: str, fcm: str) -> bool:
    try:
        push_service = FCMNotification(
            service_account_file=os.getcwd() + '/utils/dommaster_service_key.json',
            project_id="buildexgo"
        )
        result = push_service.notify(
            fcm_token=fcm,
            notification_title=message_title,
            notification_body=message_body
        )
        logger.info("FCM push result: %s", result)
        return True
    except Exception as a:
        logger.error(f"Failed while sending notification: {a}")
        return False


def send_push_to_customer(customer_id, title: str, body: str, data: dict | None = None) -> int:
    """Push to every device of the customer. Returns how many devices accepted it."""
    tokens = FcmToken.objects.filter(customer_id=customer_id).exclude(fcm_token="")
    if not tokens:
        return 0

    try:
        push_service = FCMNotification(
            service_account_file=os.getcwd() + '/utils/dommaster_service_key.json',
            project_id="buildexgo"
        )
    except Exception as e:
        logger.error("FCM client init failed: %s", e)
        return 0

    sent = 0
    seen = set()
    for token in tokens:
        if token.fcm_token in seen:
            continue
        seen.add(token.fcm_token)
        try:
            push_service.notify(
                fcm_token=token.fcm_token,
                notification_title=title,
                notification_body=body,
                data_payload=data,
            )
            sent += 1
        except FCMNotRegisteredError:
            # app removed or token rotated; other errors (network, auth) must not drop the token
            FcmToken.objects.filter(fcm_token=token.fcm_token).delete()
        except Exception as e:
            logger.error("FCM push failed: customer_id=%s token_id=%s error=%s", customer_id, token.id, e)
    return sent


def send_notification_to_customer(customer_id, enum_code=None):
    fcm_tokens = FcmToken.objects.filter(customer_id=customer_id)
    count = 0
    for token in fcm_tokens:
        result = push_notification(message_title="Buildex", message_body="message", fcm=token.fcm_token)
        if not result:
            token.delete()
            continue
        count += 1
    if count > 0:
        return True
    return False