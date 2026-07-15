import os

import requests
from django.conf import settings
from pyfcm import FCMNotification
from authorization.models import FcmToken

def send_notification(message: str) -> None:
    try:
        print(requests.get(settings.TELEGRAM_API_URL + message))
    except Exception as e:
        print(f"Failed while sending request to telegram client: {e}")



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
        print(result)
        return True
    except Exception as a:
        print(f"Failed while sending notification: {a}")
        return False


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