from django.db.models import Count, F, Max, OuterRef, Prefetch, Q, Subquery, Window
from django.db.models.functions import Coalesce, RowNumber
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.base.models import Chat, Messages
from utils.admin_views import AdminModelViewSet
from ..filters import ChatFilter, MessageFilter
from ..serializers import ChatSerializer, ChatStatsSerializer, MessageSerializer


class ChatViewSet(AdminModelViewSet):
    # a chat has nothing to edit: messages go through MessageViewSet
    http_method_names = ["get", "post", "delete", "head", "options"]
    filterset_class = ChatFilter
    search_fields = ("customer__full_name", "customer__phone_number")
    ordering_fields = ("id", "created_at", "last_activity_at", "messages_count")
    ordering = ("-last_activity_at", "-id")

    def get_queryset(self):
        last_message = Messages.objects.filter(chat=OuterRef("pk")).order_by("-created_at", "-id")
        qs = Chat.objects.annotate(
            messages_count=Count("chat_messages"),
            last_activity_at=Coalesce(Max("chat_messages__created_at"), "created_at"),
            last_is_answer=Subquery(last_message.values("is_answer")[:1]),
        )
        if self.action == "stats":
            return qs
        # one query for the last message of every chat on the page
        last_messages = Messages.objects.annotate(_row=Window(
            RowNumber(), partition_by=F("chat_id"), order_by=[F("created_at").desc(), F("id").desc()],
        )).filter(_row=1)
        return qs.select_related("customer").prefetch_related(
            Prefetch("chat_messages", queryset=last_messages, to_attr="last_messages"))

    def get_serializer_class(self):
        if self.action == "stats":
            return ChatStatsSerializer
        return ChatSerializer

    @action(detail=False, methods=["get"], pagination_class=None)
    def stats(self, request):
        """Counts over the same filters as the list."""
        data = self.filter_queryset(self.get_queryset()).aggregate(
            total=Count("id", distinct=True),
            unanswered=Count("id", filter=Q(last_is_answer=False), distinct=True),
            guests=Count("id", filter=Q(customer__isnull=True), distinct=True),
        )
        return Response(self.get_serializer(data).data)


class MessageViewSet(AdminModelViewSet):
    queryset = Messages.objects.select_related("chat")
    serializer_class = MessageSerializer
    filterset_class = MessageFilter
    search_fields = ("message",)
    ordering_fields = ("id", "created_at")
    ordering = ("-created_at", "-id")

    def perform_destroy(self, instance):
        if instance.image:
            instance.image.delete(save=False)
        instance.delete()
