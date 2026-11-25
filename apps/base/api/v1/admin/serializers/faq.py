from django.db import transaction
from rest_framework import serializers
from apps.base.faq import clean_answer, has_text
from apps.base.models import FaqItem

# both languages are required (PM decision 24.11)
REQUIRED = {"required": True, "allow_null": False, "allow_blank": False}


class FaqItemSerializer(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField(help_text="Category name in Russian.")
    page_keys = serializers.ListField(
        child=serializers.ChoiceField(choices=FaqItem.PAGE_KEYS), required=False,
        help_text="Pages the question is shown on; not sent on create = [\"faq\"].")

    class Meta:
        model = FaqItem
        fields = ("id", "category", "category_name", "question", "question_uz", "question_ru", "answer",
                  "answer_uz", "answer_ru", "page_keys", "position", "is_active", "created_at", "updated_at")
        read_only_fields = ("question", "answer", "position", "created_at", "updated_at")
        extra_kwargs = {"category": {"required": True},
                        "question_uz": REQUIRED, "question_ru": REQUIRED,
                        "answer_uz": REQUIRED, "answer_ru": REQUIRED}

    def get_category_name(self, obj) -> str:
        return dict(FaqItem.CATEGORY_CHOICES)[obj.category]

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

    @staticmethod
    def next_position(category):
        last = FaqItem.objects.filter(category=category).order_by("-position").values_list(
            "position", flat=True).first() or 0
        return last + 1

    def create(self, validated_data):
        validated_data["position"] = self.next_position(validated_data["category"])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        category = validated_data.get("category")
        if category and category != instance.category:
            validated_data["position"] = self.next_position(category)
        return super().update(instance, validated_data)


class FaqReorderSerializer(serializers.Serializer):
    """Drag & drop: `ids` of one category in the new order, list index becomes `position`; the category's
    other questions stay after them."""
    ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)

    def validate_ids(self, ids):
        if len(set(ids)) != len(ids):
            raise serializers.ValidationError("Duplicate ids.")
        rows = dict(FaqItem.objects.filter(id__in=ids).values_list("id", "category"))
        missing = set(ids) - set(rows)
        if missing:
            raise serializers.ValidationError(f"Not found: {sorted(missing)}")
        if len(set(rows.values())) > 1:
            raise serializers.ValidationError("Questions of one category only.")
        return ids

    @transaction.atomic
    def save(self, **kwargs):
        ids = self.validated_data["ids"]
        category = FaqItem.objects.values_list("category", flat=True).get(id=ids[0])
        rest = FaqItem.objects.filter(category=category).exclude(id__in=ids).order_by(
            "position", "id").values_list("id", flat=True)
        FaqItem.objects.bulk_update(
            [FaqItem(id=pk, position=position) for position, pk in enumerate([*ids, *rest], start=1)],
            ["position"],
        )
