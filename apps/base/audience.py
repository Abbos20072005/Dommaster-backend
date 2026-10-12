"""Audience of a notification: `segment` = which customers, `platform` = which of their devices.

`audience_customers` are the customers who see a targeted notification in their list,
`audience_devices` the FCM tokens its push goes to, `audience_summary` the counters of the admin form.
All of them are counted at the moment of the call — the notification keeps its own snapshot
(`NotificationRecipient`, written by `notification_push.send_push`).
"""
from datetime import timedelta

from django.db.models import Count, Exists, OuterRef, Q
from django.utils import timezone

from apps.authorization.models import Customer, CustomerAddresses, FcmToken
from apps.base.models import Notification
from apps.service.models import CartItem, Order
from utils.send_notification import real_fcm_tokens

# the city of Tashkent as a box: an address has only coordinates and a free-form name, no city
TASHKENT_LATITUDE = (41.16, 41.43)
TASHKENT_LONGITUDE = (69.10, 69.45)
BUYERS_PERIOD = timedelta(days=30)
# a cart is abandoned when it has items and nothing in it changed for a day; after a month it is forgotten
CART_ABANDONED_AFTER = timedelta(days=1)
CART_FORGOTTEN_AFTER = timedelta(days=30)
ORDER_CANCELED = 4


def segment_customers(segment):
    customers = Customer.objects.filter(is_blocked=False)
    now = timezone.now()
    if segment == Notification.PRO:
        return customers.filter(role=Customer.Role.PRORAB)
    if segment == Notification.TASHKENT:
        return customers.filter(Exists(CustomerAddresses.objects.filter(
            customer=OuterRef("pk"), latitude__range=TASHKENT_LATITUDE, longitude__range=TASHKENT_LONGITUDE,
        )))
    if segment == Notification.BUYERS_30D:
        return customers.filter(Exists(Order.objects.filter(
            customer=OuterRef("pk"), created_at__gte=now - BUYERS_PERIOD,
        ).exclude(status=ORDER_CANCELED)))
    if segment == Notification.ABANDONED_CART:
        items = CartItem.objects.filter(cart__customer=OuterRef("pk"))
        return customers.filter(
            Exists(items.filter(updated_at__gte=now - CART_FORGOTTEN_AFTER)),
            ~Exists(items.filter(updated_at__gte=now - CART_ABANDONED_AFTER)),
        )
    return customers


def audience_customers(segment, platform):
    customers = segment_customers(segment)
    if platform != Notification.PLATFORM_ALL:
        customers = customers.filter(Exists(real_fcm_tokens().filter(customer=OuterRef("pk"), platform=platform)))
    return customers


def audience_devices(segment, platform):
    devices = real_fcm_tokens().filter(customer__in=segment_customers(segment))
    if platform != Notification.PLATFORM_ALL:
        devices = devices.filter(platform=platform)
    return devices


def audience_summary():
    """Every segment with its size: customers and devices (all / ios / android)."""
    summary = []
    for segment, _ in Notification.SEGMENT_CHOICES:
        customers = segment_customers(segment)
        devices = real_fcm_tokens().filter(customer__in=customers).aggregate(
            devices=Count("fcm_token", distinct=True),
            devices_ios=Count("fcm_token", distinct=True, filter=Q(platform=FcmToken.IOS)),
            devices_android=Count("fcm_token", distinct=True, filter=Q(platform=FcmToken.ANDROID)),
        )
        summary.append({"segment": segment, "customers": customers.count(), **devices})
    return summary
