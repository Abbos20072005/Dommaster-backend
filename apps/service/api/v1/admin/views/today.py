from datetime import timedelta
from django.db.models import Count, Exists, OuterRef, Q, Subquery, Sum
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from apps.authorization.models import Customer
from apps.base.models import Banner, Chat, Messages, Notification
from apps.service.models import Order, Product, ProductAttributeValue, ProductImage, Questions, QuestionsReply
from apps.service.models.choices import PUBLISH_STATUS_DRAFT, PUBLISH_STATUS_PUBLISHED, PUBLISH_STATUS_REVIEW
from utils.admin_views import AdminViewMixin
from ..serializers import TodaySerializer, PENDING, COLLECTING, DELIVERING, CANCELED, STALE_PENDING_ORDERS, \
    REFUND_PENDING_ORDERS, UNASSIGNED_ORDERS, OUT_OF_STOCK_PRODUCTS, NO_PRICE_PRODUCTS, REVIEW_PRODUCTS, \
    UNANSWERED_QUESTIONS, UNANSWERED_CHATS, MODERATION_QUEUE, EXPIRING_BANNERS, DRAFT_NOTIFICATIONS, ORDERS, \
    CATALOG, FEEDBACK, CONTENT, DANGER, WARNING, INFO
from .dashboard import day_range, get_recent_orders

PENDING_STALE_MINUTES = 30
BANNER_EXPIRING_DAYS = 3
ATTENTION_OBJECTS = 3
CHART_DAYS = 7
RECENT_ORDERS = 10
# PAYMENT_STATUS Hold / Paid: the money is still on our side
UNREFUNDED = (1, 2)
OPEN_ORDERS = (PENDING, COLLECTING, DELIVERING)


def stale_pending_orders():
    return Order.objects.filter(status=PENDING,
                                created_at__lt=timezone.now() - timedelta(minutes=PENDING_STALE_MINUTES))


def get_cards():
    today = Q(created_at__date=timezone.now().date())  # USE_TZ=False -> naive local time
    data = Order.objects.aggregate(
        today_orders=Count("id", filter=today),
        today_total=Coalesce(Sum("total_price", filter=today), 0.0),
        pending=Count("id", filter=Q(status=PENDING)),
        collecting=Count("id", filter=Q(status=COLLECTING)),
        delivering=Count("id", filter=Q(status=DELIVERING)),
    )
    data["today_customers"] = Customer.objects.filter(today).count()
    data["stale_pending"] = stale_pending_orders().count()
    data["stale_minutes"] = PENDING_STALE_MINUTES
    return data


def attention_item(key, group, level, queryset, date_field=None, name_field=None, amount=None):
    """Attention row of `queryset` (ordered most urgent first), None when it is empty."""
    count = queryset.count()
    if not count:
        return None
    objects = [{"id": obj.id,
                "name": getattr(obj, name_field) if name_field else None,
                "date": getattr(obj, date_field) if date_field else None}
               for obj in queryset[:ATTENTION_OBJECTS]]
    return {"key": key, "group": group, "level": level, "count": count, "amount": amount,
            "date": objects[0]["date"], "objects": objects}


def get_attention():
    """Things that need an admin's action today, grouped: orders, catalog, feedback, content."""
    now = timezone.now()
    refunds = Order.objects.filter(status=CANCELED, payment_status__in=UNREFUNDED)
    active_products = Product.objects.filter(is_active=True)
    last_message = Messages.objects.filter(chat=OuterRef("pk")).order_by("-created_at", "-id")
    unanswered_chats = Chat.objects.annotate(
        last_is_answer=Subquery(last_message.values("is_answer")[:1]),
        last_message_at=Subquery(last_message.values("created_at")[:1]),
    ).filter(last_is_answer=False)
    expiring_banners = Banner.objects.filter(Banner.status_q(Banner.ACTIVE),
                                             ends_at__lte=now + timedelta(days=BANNER_EXPIRING_DAYS))
    items = [
        attention_item(STALE_PENDING_ORDERS, ORDERS, WARNING, stale_pending_orders().order_by("created_at"),
                       date_field="created_at"),
        attention_item(REFUND_PENDING_ORDERS, ORDERS, WARNING, refunds.order_by("updated_at"),
                       date_field="updated_at",
                       amount=refunds.aggregate(amount=Coalesce(Sum("total_price"), 0.0))["amount"]),
        attention_item(UNASSIGNED_ORDERS, ORDERS, INFO,
                       Order.objects.filter(status__in=OPEN_ORDERS, manager=None).order_by("created_at"),
                       date_field="created_at"),

        attention_item(OUT_OF_STOCK_PRODUCTS, CATALOG, DANGER,
                       active_products.filter(quantity__lte=0).order_by("-updated_at"), name_field="name"),
        attention_item(NO_PRICE_PRODUCTS, CATALOG, DANGER,
                       active_products.filter(price__lte=0).order_by("-updated_at"), name_field="name"),
        attention_item(REVIEW_PRODUCTS, CATALOG, INFO,
                       Product.objects.filter(publish_status=PUBLISH_STATUS_REVIEW).order_by("updated_at"),
                       name_field="name"),

        attention_item(UNANSWERED_QUESTIONS, FEEDBACK, WARNING,
                       Questions.objects.filter(is_visible=True).exclude(question_reply__is_admin=True)
                       .order_by("created_at"), date_field="created_at", name_field="question"),
        attention_item(UNANSWERED_CHATS, FEEDBACK, WARNING, unanswered_chats.order_by("last_message_at"),
                       date_field="last_message_at"),
        attention_item(MODERATION_QUEUE, FEEDBACK, INFO,
                       QuestionsReply.objects.filter(is_visible=False, is_admin=False).order_by("created_at"),
                       date_field="created_at", name_field="answer"),

        attention_item(EXPIRING_BANNERS, CONTENT, WARNING, expiring_banners.order_by("ends_at"),
                       date_field="ends_at", name_field="title"),
        attention_item(DRAFT_NOTIFICATIONS, CONTENT, INFO,
                       Notification.objects.filter(Notification.status_q(Notification.DRAFT)).order_by("publish_at"),
                       date_field="publish_at", name_field="title"),
    ]
    items = [item for item in items if item]
    return {"total": len(items), "banner_days": BANNER_EXPIRING_DAYS, "items": items}


def get_catalog():
    """Publication state of all products + what the active (shown to customers) ones are missing."""
    active = Q(is_active=True)
    no_translation = Q(name_uz__isnull=True) | Q(name_uz="") | Q(name_ru__isnull=True) | Q(name_ru="")
    no_image = Q(has_image=False)
    # characteristics of a product = its attribute values
    no_characteristics = Q(has_attribute_values=False)
    return Product.objects.annotate(
        has_image=Exists(ProductImage.objects.filter(product=OuterRef("pk"))),
        has_attribute_values=Exists(ProductAttributeValue.objects.filter(product=OuterRef("pk"))),
    ).aggregate(
        published=Count("id", filter=Q(publish_status=PUBLISH_STATUS_PUBLISHED)),
        draft=Count("id", filter=Q(publish_status=PUBLISH_STATUS_DRAFT)),
        review=Count("id", filter=Q(publish_status=PUBLISH_STATUS_REVIEW)),
        incomplete=Count("id", filter=active & (no_translation | no_image | no_characteristics)),
        no_translation=Count("id", filter=active & no_translation),
        no_image=Count("id", filter=active & no_image),
        no_characteristics=Count("id", filter=active & no_characteristics),
        out_of_stock=Count("id", filter=active & Q(quantity__lte=0)),
    )


def get_orders_chart():
    """Created orders per day over the last `CHART_DAYS` days incl. today."""
    start, _, dates = day_range(CHART_DAYS)
    rows = Order.objects.filter(created_at__date__gte=start) \
        .annotate(day=TruncDate("created_at")).values("day") \
        .annotate(count=Count("id"), total=Coalesce(Sum("total_price"), 0.0))
    by_day = {row["day"]: row for row in rows}

    points = [{"date": day, "count": by_day.get(day, {}).get("count", 0),
               "total": by_day.get(day, {}).get("total", 0.0)} for day in dates]
    count = sum(p["count"] for p in points)
    return {"days": CHART_DAYS, "count": count, "average_per_day": round(count / CHART_DAYS), "points": points}


class TodayAPIView(AdminViewMixin, GenericAPIView):
    """"Today's tasks" page, all widgets in one response."""
    serializer_class = TodaySerializer
    filter_backends = []
    pagination_class = None

    def get(self, request):
        data = {
            "now": timezone.now(),
            "cards": get_cards(),
            "attention": get_attention(),
            "catalog": get_catalog(),
            "orders_chart": get_orders_chart(),
            "recent_orders": get_recent_orders(RECENT_ORDERS),
        }
        return Response(self.get_serializer(data).data)
