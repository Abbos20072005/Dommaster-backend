from django.db import transaction
from django.db.models import Count
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from apps.base import faq
from apps.base.models import FaqItem, FaqTopic
from utils.admin_views import AdminModelViewSet
from ..filters import FaqItemFilter
from ..serializers import FaqItemSerializer, FaqReorderSerializer, FaqTopicSerializer


class FaqCacheMixin:
    """The client list is cached 15 min; an admin change drops it at once."""

    def perform_create(self, serializer):
        super().perform_create(serializer)
        transaction.on_commit(faq.clear_cache)

    def perform_update(self, serializer):
        super().perform_update(serializer)
        transaction.on_commit(faq.clear_cache)

    def perform_destroy(self, instance):
        super().perform_destroy(instance)
        transaction.on_commit(faq.clear_cache)

    @action(detail=False, methods=["post"], serializer_class=FaqReorderSerializer)
    def reorder(self, request):
        """Drag & drop: `ids` in the new order, list index becomes `position`."""
        serializer = FaqReorderSerializer(data=request.data, context={"model": self.queryset.model})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        transaction.on_commit(faq.clear_cache)
        return Response(serializer.data)


class FaqTopicViewSet(FaqCacheMixin, AdminModelViewSet):
    queryset = FaqTopic.objects.annotate(items_count=Count("items"))
    serializer_class = FaqTopicSerializer
    filterset_fields = ("is_active",)
    search_fields = ("name_ru", "name_uz", "slug")
    ordering_fields = ("id", "position", "name_ru", "name_uz", "items_count", "created_at", "updated_at")
    ordering = ("position", "id")

    def perform_destroy(self, instance):
        if instance.items.exists():
            raise ValidationError({"detail": "Topic has questions, move or delete them first "
                                             "(or deactivate the topic: is_active=false)."})
        super().perform_destroy(instance)


class FaqItemViewSet(FaqCacheMixin, AdminModelViewSet):
    queryset = FaqItem.objects.select_related("topic")
    serializer_class = FaqItemSerializer
    filterset_class = FaqItemFilter
    search_fields = ("question_ru", "question_uz", "answer_ru", "answer_uz")
    ordering_fields = ("id", "position", "created_at", "updated_at")
    ordering = ("topic__position", "topic_id", "position", "id")
