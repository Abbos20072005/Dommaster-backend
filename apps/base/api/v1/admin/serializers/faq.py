from django.db import transaction
from rest_framework import serializers
from apps.base.faq import clean_answer, has_text
from apps.base.models import FaqItem, FaqTopic
from utils.admin_serializers import RelationSerializer

# both languages are required (PM decision 24.11)
REQUIRED = {"required": True, "allow_null": False, "allow_blank": False}


class FaqTopicSerializer(serializers.ModelSerializer):
    items_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = FaqTopic
        fields = ("id", "name", "name_uz", "name_ru", "slug", "position", "is_active", "items_count",
                  "created_at", "updated_at")
        read_only_fields = ("name", "position", "created_at", "updated_at")
        extra_kwargs = {"name_uz": REQUIRED, "name_ru": REQUIRED}

    def create(self, validated_data):
        last = FaqTopic.objects.order_by("-position").values_list("position", flat=True).first() or 0
        validated_data["position"] = last + 1
        return super().create(validated_data)


class FaqTopicRelationSerializer(RelationSerializer):
    class Meta:
        model = FaqTopic
        fields = ("id", "name", "slug", "is_active")


class FaqItemSerializer(serializers.ModelSerializer):
    topic = FaqTopicRelationSerializer()
    page_keys = serializers.ListField(
        child=serializers.ChoiceField(choices=FaqItem.PAGE_KEYS), required=False,
        help_text="Pages the question is shown on; not sent on create = [\"faq\"].")

    class Meta:
        model = FaqItem
        fields = ("id", "topic", "question", "question_uz", "question_ru", "answer", "answer_uz", "answer_ru",
                  "page_keys", "position", "is_active", "created_at", "updated_at")
        read_only_fields = ("question", "answer", "position", "created_at", "updated_at")
        extra_kwargs = {"question_uz": REQUIRED, "question_ru": REQUIRED,
                        "answer_uz": REQUIRED, "answer_ru": REQUIRED}

    def validate_page_keys(self, value):
        return list(dict.fromkeys(value))

    def _clean_answer(self, value):
        value = clean_answer(value)
        if not has_text(value):
            raise serializers.ValidationError("The answer has no text after cleaning.")
        return value

    def validate_answer_uz(self, value):
        return self._clean_answer(value)

    def validate_answer_ru(self, value):
        return self._clean_answer(value)

    def create(self, validated_data):
        last = FaqItem.objects.filter(topic=validated_data["topic"]).order_by("-position").values_list(
            "position", flat=True).first() or 0
        validated_data["position"] = last + 1
        return super().create(validated_data)

    def update(self, instance, validated_data):
        topic = validated_data.get("topic")
        if topic and topic.pk != instance.topic_id:
            last = FaqItem.objects.filter(topic=topic).order_by("-position").values_list(
                "position", flat=True).first() or 0
            validated_data["position"] = last + 1
        return super().update(instance, validated_data)


class FaqReorderSerializer(serializers.Serializer):
    """Drag & drop: `ids` in the new order, list index becomes `position`; rows not sent stay after them.
    Questions: the ids of one topic, the topic's other questions stay after them."""
    ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)

    def validate_ids(self, ids):
        if len(set(ids)) != len(ids):
            raise serializers.ValidationError("Duplicate ids.")
        model = self.context["model"]
        rows = dict(model.objects.filter(id__in=ids).values_list(
            "id", "topic_id" if model is FaqItem else "id"))
        missing = set(ids) - set(rows)
        if missing:
            raise serializers.ValidationError(f"Not found: {sorted(missing)}")
        if model is FaqItem and len(set(rows.values())) > 1:
            raise serializers.ValidationError("Questions of one topic only.")
        return ids

    @transaction.atomic
    def save(self, **kwargs):
        model = self.context["model"]
        ids = self.validated_data["ids"]
        rest = model.objects.exclude(id__in=ids)
        if model is FaqItem:
            rest = rest.filter(topic_id=model.objects.get(id=ids[0]).topic_id)
        rest = rest.order_by("position", "id").values_list("id", flat=True)
        model.objects.bulk_update(
            [model(id=pk, position=position) for position, pk in enumerate([*ids, *rest], start=1)],
            ["position"],
        )
