from rest_framework import serializers
from apps.authorization.models import Customer
from apps.base.models import Chat, Messages
from utils.admin_serializers import RelationSerializer


class ChatCustomerSerializer(RelationSerializer):
    class Meta:
        model = Customer
        fields = ("id", "full_name", "phone_number")


class ChatLastMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Messages
        fields = ("id", "message", "image", "is_answer", "created_at")

    def get_attribute(self, instance):
        # prefetched by ChatViewSet (`last_messages`), queried otherwise (e.g. right after create)
        messages = getattr(instance, "last_messages", None)
        if messages is None:
            messages = instance.chat_messages.order_by("-created_at", "-id")[:1]
        return messages[0] if messages else None


class ChatSerializer(serializers.ModelSerializer):
    # null for guest chats (identified by the `chat_token` cookie, not exposed)
    customer = ChatCustomerSerializer()
    last_message = ChatLastMessageSerializer(read_only=True, allow_null=True)
    messages_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Chat
        fields = ("id", "customer", "last_message", "messages_count", "created_at", "updated_at")
        read_only_fields = ("created_at", "updated_at")

    def validate_customer(self, value):
        # the client API reads a customer's chat with .first(): keep one per customer
        if Chat.objects.filter(customer=value).exists():
            raise serializers.ValidationError("This customer already has a chat.")
        return value


class ChatStatsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    unanswered = serializers.IntegerField(help_text="Last message is the customer's")
    guests = serializers.IntegerField(help_text="Chats without a customer (cookie)")


class MessageChatSerializer(RelationSerializer):
    class Meta:
        model = Chat
        fields = ("id",)


class MessageSerializer(serializers.ModelSerializer):
    """Messages created here are the admin's answers (is_answer); customers' messages are read-only."""
    chat = MessageChatSerializer()

    class Meta:
        model = Messages
        fields = ("id", "chat", "message", "image", "is_answer", "created_at", "updated_at")
        read_only_fields = ("is_answer", "created_at", "updated_at")

    def validate(self, attrs):
        instance = self.instance
        if instance:
            if not instance.is_answer:
                raise serializers.ValidationError({"detail": "Customer messages can't be edited."})
            if "chat" in attrs and attrs["chat"] != instance.chat:
                raise serializers.ValidationError({"chat": "Can't be changed after creation."})
        message = attrs.get("message", instance.message if instance else None)
        image = attrs.get("image", instance.image if instance else None)
        if not message and not image:
            raise serializers.ValidationError({"message": "Send a message text or an image."})
        return attrs

    def create(self, validated_data):
        return super().create({**validated_data, "is_answer": True})
