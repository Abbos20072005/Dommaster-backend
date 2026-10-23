import os

from django.db import transaction
from rest_framework import serializers

from apps.service import content_import
from apps.service.models import ContentImport, ContentImportChange, Product
from utils.background import run_in_background
from .moderation import ModerationStaffSerializer


class ContentExportQuerySerializer(serializers.Serializer):
    languages = serializers.CharField(required=False, help_text="uz,ru (default: all) — the text columns to export")
    incomplete = serializers.BooleanField(required=False, default=False,
                                          help_text="Only products with an empty editable field")

    def validate_languages(self, value):
        langs = [lang.strip() for lang in value.split(",") if lang.strip()]
        unknown = set(langs) - set(content_import.languages())
        if not langs or unknown:
            raise serializers.ValidationError(f"Allowed: {', '.join(content_import.languages())}")
        return [lang for lang in content_import.languages() if lang in langs]


class ContentImportListSerializer(serializers.ModelSerializer):
    created_by = ModerationStaffSerializer(read_only=True)
    applied_by = ModerationStaffSerializer(read_only=True)

    class Meta:
        model = ContentImport
        fields = ("id", "file_name", "status", "created_by", "created_at", "applied_by", "applied_at", "languages",
                  "rows_total", "rows_changed", "rows_unchanged", "rows_error", "changes_count")
        read_only_fields = fields


class ContentImportSerializer(ContentImportListSerializer):
    file = serializers.FileField(help_text="The XLSX of `products/content-export/`")

    class Meta(ContentImportListSerializer.Meta):
        fields = ContentImportListSerializer.Meta.fields + ("file", "columns", "ignored_columns", "errors", "error")
        read_only_fields = tuple(field for field in fields if field != "file")

    def validate_file(self, file):
        if os.path.splitext(file.name)[1].lower() != ".xlsx":
            raise serializers.ValidationError("Only .xlsx files")
        if file.size > content_import.MAX_FILE_SIZE:
            raise serializers.ValidationError(f"Max {content_import.MAX_FILE_SIZE // (1024 * 1024)} MB")
        return file

    def create(self, validated_data):
        from apps.service import tasks
        instance = ContentImport.objects.create(
            file=validated_data["file"], file_name=validated_data["file"].name[:255],
            created_by=self.context["request"].user)
        transaction.on_commit(lambda: run_in_background(tasks.validate_content_import, instance.pk))
        return instance


class ContentImportProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ("id", "name", "product_code")


class ContentImportChangeSerializer(serializers.ModelSerializer):
    product = ContentImportProductSerializer(read_only=True)

    class Meta:
        model = ContentImportChange
        fields = ("id", "row", "product", "field", "old_value", "new_value")
        read_only_fields = fields
