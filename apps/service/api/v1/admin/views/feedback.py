from django.db.models import Avg, Count, Q
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.service.models import Comment, CommentReply, CommentImages, Questions, QuestionsReply
from utils.admin_views import AdminModelViewSet
from ..filters import CommentFilter, QuestionFilter, CommentReplyFilter, QuestionReplyFilter, comment_answered, \
    question_answered
from ..serializers import CommentListSerializer, CommentSerializer, CommentStatsSerializer, QuestionListSerializer, \
    QuestionSerializer, QuestionStatsSerializer, CommentReplySerializer, QuestionReplySerializer

# comments/questions are written by customers: the admin only moderates them (no create)
MODERATION_METHODS = ["get", "put", "patch", "delete", "head", "options"]


class CommentViewSet(AdminModelViewSet):
    http_method_names = MODERATION_METHODS
    filterset_class = CommentFilter
    search_fields = ("comment", "customer__full_name", "customer__phone_number", "product__name_ru",
                     "product__product_code")
    ordering_fields = ("id", "product_rating", "created_at", "updated_at")
    ordering = ("-created_at",)

    def get_queryset(self):
        qs = Comment.objects.all()
        if self.action == "stats":
            return qs
        qs = qs.select_related("customer", "product").prefetch_related("comment_image") \
            .annotate(replies_count=Count("comment_reply"))
        if self.action != "list":
            qs = qs.prefetch_related("comment_reply__customer")
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return CommentListSerializer
        if self.action == "stats":
            return CommentStatsSerializer
        return CommentSerializer

    @action(detail=True, methods=["delete"], url_path=r"images/(?P<image_id>[0-9]+)")
    def delete_image(self, request, pk=None, image_id=None):
        image = get_object_or_404(CommentImages, pk=image_id, comment_id=pk)
        image.image.delete(save=False)
        image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], pagination_class=None)
    def stats(self, request):
        """Counts over the same filters as the list (?product=&from_created=...)."""
        data = self.filter_queryset(self.get_queryset()).annotate(_answered=comment_answered()).aggregate(
            total=Count("id"),
            visible=Count("id", filter=Q(is_visible=True)),
            hidden=Count("id", filter=Q(is_visible=False)),
            unanswered=Count("id", filter=Q(_answered=False)),
            average_rating=Coalesce(Avg("product_rating"), 0.0),
        )
        return Response(self.get_serializer(data).data)


class QuestionViewSet(AdminModelViewSet):
    http_method_names = MODERATION_METHODS
    filterset_class = QuestionFilter
    search_fields = ("question", "customer__full_name", "customer__phone_number", "product__name_ru",
                     "product__product_code")
    ordering_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)

    def get_queryset(self):
        qs = Questions.objects.all()
        if self.action == "stats":
            return qs
        qs = qs.select_related("customer", "product").annotate(replies_count=Count("question_reply"))
        if self.action != "list":
            qs = qs.prefetch_related("question_reply__customer")
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return QuestionListSerializer
        if self.action == "stats":
            return QuestionStatsSerializer
        return QuestionSerializer

    @action(detail=False, methods=["get"], pagination_class=None)
    def stats(self, request):
        """Counts over the same filters as the list (?product=&from_created=...)."""
        questions = self.filter_queryset(self.get_queryset())
        data = questions.annotate(_answered=question_answered()).aggregate(
            total=Count("id"),
            visible=Count("id", filter=Q(is_visible=True)),
            hidden=Count("id", filter=Q(is_visible=False)),
            unanswered=Count("id", filter=Q(is_visible=True, _answered=False)),
        )
        data["moderation_queue"] = QuestionsReply.objects.filter(
            question__in=questions, is_visible=False, is_admin=False).count()
        return Response(self.get_serializer(data).data)


class CommentReplyViewSet(AdminModelViewSet):
    queryset = CommentReply.objects.select_related("customer", "comment")
    serializer_class = CommentReplySerializer
    filterset_class = CommentReplyFilter
    search_fields = ("reply_comment", "customer__full_name", "customer__phone_number")
    ordering_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)


class QuestionReplyViewSet(AdminModelViewSet):
    queryset = QuestionsReply.objects.select_related("customer", "question")
    serializer_class = QuestionReplySerializer
    filterset_class = QuestionReplyFilter
    search_fields = ("answer", "customer__full_name", "customer__phone_number")
    ordering_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)
