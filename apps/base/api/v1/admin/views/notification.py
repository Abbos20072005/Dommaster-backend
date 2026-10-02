from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.base.models import Notification, NotificationRead
from utils.admin_views import AdminModelViewSet
from ..filters import NotificationFilter
from ..serializers import NotificationSerializer, NotificationStatsSerializer


class NotificationViewSet(AdminModelViewSet):
    queryset = Notification.objects.annotate(reads_count=Count("reads"))
    serializer_class = NotificationSerializer
    filterset_class = NotificationFilter
    search_fields = ("title_ru", "title_uz", "title_en", "description_ru", "description_uz", "description_en",
                     "deeplink")
    ordering_fields = ("id", "title", "publish_at", "is_active", "reads_count", "created_at", "updated_at")
    ordering = ("-publish_at", "-id")

    @action(detail=False, methods=["get"], filter_backends=[], pagination_class=None,
            serializer_class=NotificationStatsSerializer)
    def stats(self, request):
        """Cards and tab counters of the notifications page (all notifications, list filters are not applied)."""
        since = timezone.now() - timedelta(days=30)
        published = Notification.status_q(Notification.PUBLISHED)
        data = Notification.objects.aggregate(
            published=Count("id", filter=published),
            scheduled=Count("id", filter=Notification.status_q(Notification.SCHEDULED)),
            draft=Count("id", filter=Notification.status_q(Notification.DRAFT)),
            published_30d=Count("id", filter=published & Q(publish_at__gte=since)),
        )
        data["reads_30d"] = NotificationRead.objects.filter(created_at__gte=since).count()
        return Response(self.get_serializer(data).data)
