from rest_framework import serializers

from apps.service.assistant.service import MESSAGE_MAX_LENGTH
from apps.service.models import AssistantMessage, ORDER_CHANNEL
from .serializers import ProductSerializer


class AssistantChatSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=MESSAGE_MAX_LENGTH, trim_whitespace=True)
    # the conversation to continue; missing / not the caller's -> a new conversation
    conversation_id = serializers.IntegerField(required=False, allow_null=True)
    platform = serializers.ChoiceField(choices=ORDER_CHANNEL, required=False, allow_blank=True, default="")


class AssistantProductSerializer(ProductSerializer):
    # in_stock / low / check (the stock number is not reliable: ask to check) / out_of_stock
    stock_status = serializers.ChoiceField(choices=["in_stock", "low", "check", "out_of_stock"], read_only=True)

    class Meta(ProductSerializer.Meta):
        fields = (*ProductSerializer.Meta.fields, "stock_status")


class AssistantQuestionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    text = serializers.CharField(help_text="The message as saved: phone / card numbers masked")
    pii_masked = serializers.BooleanField()


class AssistantReplySerializer(serializers.Serializer):
    conversation_id = serializers.IntegerField()
    message_id = serializers.IntegerField()
    question = AssistantQuestionSerializer()
    text = serializers.CharField()
    operator = serializers.BooleanField(help_text="Show the \"contact the operator\" button under the answer")
    products = AssistantProductSerializer(many=True)


class AssistantHistoryMessageSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    role = serializers.ChoiceField(choices=AssistantMessage.ROLE_CHOICES)
    text = serializers.CharField()
    pii_masked = serializers.BooleanField()
    operator = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    products = AssistantProductSerializer(many=True)


class AssistantConversationSerializer(serializers.Serializer):
    conversation_id = serializers.IntegerField()
    messages = AssistantHistoryMessageSerializer(many=True)
