from rest_framework import serializers
from apps.authorization.models import Customer
from apps.service.models import Product, Comment, CommentReply, CommentImages, Questions, QuestionsReply
from utils.admin_serializers import RelationSerializer


class FeedbackCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ("id", "full_name", "phone_number")


class FeedbackProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ("id", "name", "product_code")


class CommentImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommentImages
        fields = ("id", "image", "created_at")


class CommentReplyShortSerializer(serializers.ModelSerializer):
    customer = FeedbackCustomerSerializer(read_only=True)

    class Meta:
        model = CommentReply
        fields = ("id", "customer", "reply_comment", "is_admin", "is_visible", "created_at")


class QuestionReplyShortSerializer(serializers.ModelSerializer):
    customer = FeedbackCustomerSerializer(read_only=True)

    class Meta:
        model = QuestionsReply
        fields = ("id", "customer", "answer", "is_admin", "is_visible", "created_at")


class CommentListSerializer(serializers.ModelSerializer):
    customer = FeedbackCustomerSerializer(read_only=True)
    product = FeedbackProductSerializer(read_only=True)
    images = CommentImageSerializer(source="comment_image", many=True, read_only=True)
    replies_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Comment
        fields = ("id", "customer", "product", "product_rating", "comment", "is_visible", "images", "replies_count",
                  "created_at", "updated_at")
        # written by customers: the admin moderates the text/visibility, the rating stays the customer's
        read_only_fields = ("product_rating", "created_at", "updated_at")


class CommentSerializer(CommentListSerializer):
    replies = CommentReplyShortSerializer(source="comment_reply", many=True, read_only=True)

    class Meta(CommentListSerializer.Meta):
        fields = CommentListSerializer.Meta.fields + ("replies",)


class QuestionListSerializer(serializers.ModelSerializer):
    customer = FeedbackCustomerSerializer(read_only=True)
    product = FeedbackProductSerializer(read_only=True)
    replies_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Questions
        fields = ("id", "customer", "product", "question", "is_visible", "replies_count", "created_at", "updated_at")
        read_only_fields = ("created_at", "updated_at")


class QuestionSerializer(QuestionListSerializer):
    replies = QuestionReplyShortSerializer(source="question_reply", many=True, read_only=True)

    class Meta(QuestionListSerializer.Meta):
        fields = QuestionListSerializer.Meta.fields + ("replies",)


class ReplyCommentSerializer(RelationSerializer):
    class Meta:
        model = Comment
        fields = ("id", "comment")


class ReplyQuestionSerializer(RelationSerializer):
    class Meta:
        model = Questions
        fields = ("id", "question")


class ReplyBaseSerializer(serializers.ModelSerializer):
    """Replies created here are the admin's (is_admin, no customer); customers' replies are only moderated."""
    parent_field = None
    customer = FeedbackCustomerSerializer(read_only=True)

    def validate(self, attrs):
        if self.instance and self.parent_field in attrs \
                and attrs[self.parent_field] != getattr(self.instance, self.parent_field):
            raise serializers.ValidationError({self.parent_field: "Can't be changed after creation."})
        return attrs

    def create(self, validated_data):
        # QuestionsReply.is_visible defaults to False (moderation) - the admin's own answer is published
        validated_data.setdefault("is_visible", True)
        return super().create({**validated_data, "is_admin": True, "customer": None})


class CommentReplySerializer(ReplyBaseSerializer):
    parent_field = "comment"
    comment = ReplyCommentSerializer()

    class Meta:
        model = CommentReply
        fields = ("id", "comment", "customer", "reply_comment", "is_admin", "is_visible", "created_at", "updated_at")
        read_only_fields = ("is_admin", "created_at", "updated_at")


class QuestionReplySerializer(ReplyBaseSerializer):
    parent_field = "question"
    question = ReplyQuestionSerializer()

    class Meta:
        model = QuestionsReply
        fields = ("id", "question", "customer", "answer", "is_admin", "is_visible", "created_at", "updated_at")
        read_only_fields = ("is_admin", "created_at", "updated_at")


class CommentStatsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    visible = serializers.IntegerField()
    hidden = serializers.IntegerField()
    unanswered = serializers.IntegerField(help_text="No admin reply")
    average_rating = serializers.FloatField()


class QuestionStatsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    visible = serializers.IntegerField()
    hidden = serializers.IntegerField()
    unanswered = serializers.IntegerField(help_text="Visible, no admin answer")
    moderation_queue = serializers.IntegerField(help_text="Hidden customer answers to these questions")
