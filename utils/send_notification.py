import os
import logging
from concurrent.futures import ThreadPoolExecutor

import requests
from django.conf import settings
from django.db.models import F
from pyfcm import FCMNotification
from pyfcm.errors import FCMNotRegisteredError
from apps.authorization.models import FcmToken

logger = logging.getLogger(__name__)

PUSH_WORKERS = 8

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


def real_fcm_tokens():
    # `phone_auth` stores the device id as a placeholder until the app sends the real token
    return FcmToken.objects.exclude(fcm_token="").exclude(fcm_token=F("device_id"))


def send_push_to_all(title: str, body: str, data: dict | None = None) -> int:
    """Push to every registered device of every customer. Returns how many devices accepted it."""
    tokens = list(real_fcm_tokens().values_list("fcm_token", flat=True).distinct())
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

    def send(fcm_token):
        """True = accepted, None = the token is dead, False = any other failure."""
        try:
            push_service.notify(fcm_token=fcm_token, notification_title=title, notification_body=body,
                                data_payload=data)
            return True
        except FCMNotRegisteredError:
            return None
        except Exception as e:
            logger.error("FCM push failed: error=%s", e)
            return False

    # one request per device: a few threads keep a large audience within minutes
    # (pyfcm holds a requests session per thread)
    with ThreadPoolExecutor(max_workers=PUSH_WORKERS) as pool:
        results = list(pool.map(send, tokens))

    # the workers don't touch the database, so no connections are left open in them
    dead = [token for token, result in zip(tokens, results) if result is None]
    if dead:
        FcmToken.objects.filter(fcm_token__in=dead).delete()
    return sum(1 for result in results if result)


def send_push_to_customer(customer_id, title: str, body: str, data: dict | None = None) -> int:
    """Push to every device of the customer. Returns how many devices accepted it."""
    tokens = real_fcm_tokens().filter(customer_id=customer_id)
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