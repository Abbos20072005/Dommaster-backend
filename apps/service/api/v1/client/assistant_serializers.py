from rest_framework import serializers

from apps.service.assistant.service import MESSAGE_MAX_LENGTH
from apps.service.models import AssistantMessage, ORDER_CHANNEL
from .serializers import ProductSerializer


class AssistantChatSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=MESSAGE_MAX_LENGTH, trim_whitespace=True)
    # the conversation to continue; missing / not the caller's -> a new conversation
    conversation_id = serializers.IntegerField(required=False, allow_null=True)
    platform = serializers.ChoiceField(choices=ORDER_CHANNEL, required=False, allow_blank=True, default="")


class AssistantReplySerializer(serializers.Serializer):
    conversation_id = serializers.IntegerField()
    message_id = serializers.IntegerField()
    text = serializers.CharField()
    products = ProductSerializer(many=True)


class AssistantHistoryMessageSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    role = serializers.ChoiceField(choices=AssistantMessage.ROLE_CHOICES)
    text = serializers.CharField()
    created_at = serializers.DateTimeField()
    products = ProductSerializer(many=True)


class AssistantConversationSerializer(serializers.Serializer):
    conversation_id = serializers.IntegerField()
    messages = AssistantHistoryMessageSerializer(many=True)
