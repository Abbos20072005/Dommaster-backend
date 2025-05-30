import os

import requests
from django.conf import settings
from pyfcm import FCMNotification


def send_notification(message: str) -> None:
    try:
        print(requests.get(settings.TELEGRAM_API_URL + message))
    except Exception as e:
        print(f"Failed while sending request to telegram client: {e}")



def push_notification(message_title: str, message_body: str, fcm: str) -> bool:
    """
    Sends a push notification to a user.

    :param message_title: The title of the notification message.
    :param message_body: The body/content of the notification message.
    :param fcm: The FCM (Firebase Cloud Messaging) token of the user to receive the notification.
    :return: True if the push notification was successful, otherwise False.
    """
    push_service = FCMNotification(
        service_account_file=os.getcwd() + '/utils/dommaster_service_key.json',
        project_id="dommaster-2d7e4"
    )
    try:
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


# def send_notification_to_members(contract, sender, taker_id, enum_code):
#     fcm_tokens = FcmToken.objects.filter(user_id=taker_id, status=True)
#     count = 0
#     for token in fcm_tokens:
#         result = push_notification(message_title='Haq', message_body="message", fcm=token.fcm_token)
#         if not result:
#             token.status = False
#             token.save()
#             continue
#         count += 1
#     if count > 0:
#         return True
#     return False