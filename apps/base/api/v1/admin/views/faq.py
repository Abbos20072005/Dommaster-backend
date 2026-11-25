from django.db import transaction
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.base import faq
from apps.base.models import FaqItem
from utils.admin_views import AdminModelViewSet
from ..filters import FaqItemFilter
from ..serializers import FaqItemSerializer, FaqReorderSerializer


class FaqItemViewSet(AdminModelViewSet):
    """FAQ questions. The categories are a fixed list (`FaqItem.CATEGORIES`), not an endpoint of their own.
    The client list is cached 15 min; every admin change drops it at once."""
    queryset = FaqItem.objects.annotate(category_rank=faq.category_order())
    serializer_class = FaqItemSerializer
    filterset_class = FaqItemFilter
    search_fields = ("question_ru", "question_uz", "answer_ru", "answer_uz")
    ordering_fields = ("id", "position", "created_at", "updated_at")
    ordering = ("category_rank", "position", "id")

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
        """Drag & drop: `ids` of one category in the new order, list index becomes `position`."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        transaction.on_commit(faq.clear_cache)
        return Response(serializer.data)
