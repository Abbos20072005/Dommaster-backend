import base64
import uuid
import os
import re
from django.db import transaction
from django.core.files.base import ContentFile
from django.utils.text import slugify
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from dotenv import load_dotenv

from exceptions.error_exception import CustomApiException
from exceptions.error_messages import ErrorCodes
from service.models import (
    Product, ProductImage, ProductCharacteristics,
    ProductItemCategory,
    Brand, ProductItemCategoryFilterSchema, ProductFilterNumericValue,
)

load_dotenv()

INTEGRATION_API_KEY = os.getenv("INTEGRATION_1C_API_KEY", "default-1c-api-key-change-me")

NUMERIC_UNITS = {"kg", "g", "l", "m", "sm", "cm", "mm", "kw", "w", "v", "a"}


def decode_base64_image(base64_string):
    try:
        if ";" in base64_string:
            format_str, img_data = base64_string.split(";base64,")
            ext = format_str.split("/")[-1]
        else:
            img_data = base64_string
            ext = "jpg"

        if ext not in ("jpg", "jpeg", "png", "webp", "gif"):
            ext = "jpg"

        decoded = base64.b64decode(img_data)
        return ContentFile(decoded, name=f"{uuid.uuid4().hex}.{ext}")
    except Exception:
        raise CustomApiException(error_code=ErrorCodes.INTEGRATION_IMAGE_DECODE_FAILED)


def get_or_create_brand(guid):
    if not guid:
        return None
    brand = Brand.objects.filter(guid=guid).first()
    if brand:
        return brand
    brand = Brand.objects.create(
        name=guid,
        name_uz=guid,
        name_en=guid,
        guid=guid,
    )
    return brand


def make_filter_key(name_ru):
    return slugify(name_ru, allow_unicode=True) or slugify(name_ru, allow_unicode=False)


def parse_numeric(raw_value):
    if not raw_value:
        return None
    cleaned = re.sub(r'[^\d.,]', '', str(raw_value)).replace(',', '.')
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def detect_filter_type(schema, raw_value, unit, item_category):
    if schema.type_locked:
        return schema.type

    if unit and unit.lower() in NUMERIC_UNITS:
        return "range"

    existing_count = ProductFilterNumericValue.objects.filter(schema=schema).count()
    total_count = Product.objects.filter(
        product_item_category=item_category,
        is_active=True,
        filter_data__has_key=schema.key
    ).count() if schema.key else 0

    is_numeric = parse_numeric(raw_value) is not None

    if total_count == 0:
        return "range" if is_numeric else "checkbox"

    numeric_ratio = existing_count / max(total_count, 1)
    if is_numeric and numeric_ratio > 0.5:
        return "range"

    return "checkbox"


class OneCProductInputSerializer(serializers.Serializer):
    api_key = serializers.CharField(required=True, write_only=True)
    name = serializers.CharField(required=True)
    name_uz = serializers.CharField(required=False, allow_blank=True)
    name_en = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    description_uz = serializers.CharField(required=False, allow_blank=True)
    description_en = serializers.CharField(required=False, allow_blank=True)
    price = serializers.FloatField(required=True)
    unit = serializers.ChoiceField(choices=[
        "kg", "l", "sm", "pcs", "m", "g", "pkg", "set"
    ], default="pcs")
    quantity = serializers.IntegerField(default=0)
    discount_price = serializers.FloatField(required=False, allow_null=True)
    discount = serializers.IntegerField(required=False, allow_null=True)
    item_category_id = serializers.IntegerField(required=False, allow_null=True)
    brand_guid = serializers.CharField(required=False, allow_blank=True)
    vendor_code = serializers.CharField(required=False, allow_blank=True)
    barcode = serializers.CharField(required=False, allow_blank=True)
    product_guid = serializers.CharField(required=False, allow_blank=True)
    characteristics = serializers.ListField(
        required=False, default=list,
        child=serializers.DictField()
    )
    images_base64 = serializers.ListField(
        required=False, default=list,
        child=serializers.CharField()
    )
    is_active = serializers.BooleanField(default=True)


class OneCIntegrationViewSet(ViewSet):
    @swagger_auto_schema(
        operation_summary="1C Product create",
        operation_description="Create product from 1C with images, characteristics, attributes",
        request_body=OneCProductInputSerializer(),
        responses={201: "Product created"},
        tags=["1C Integration"]
    )
    def product_create(self, request):
        serializer = OneCProductInputSerializer(data=request.data)
        if not serializer.is_valid():
            raise CustomApiException(
                error_code=ErrorCodes.INTEGRATION_INVALID_DATA,
                message=serializer.errors
            )

        data = serializer.validated_data

        if data.get("api_key") != INTEGRATION_API_KEY:
            raise CustomApiException(error_code=ErrorCodes.INTEGRATION_API_KEY_INVALID)

        with transaction.atomic():
            item_category_id = data.get("item_category_id")
            if item_category_id:
                item_category = ProductItemCategory.objects.filter(id=item_category_id).first()
                if not item_category:
                    raise CustomApiException(
                        error_code=ErrorCodes.INTEGRATION_INVALID_DATA,
                        message=f"item_category_id {item_category_id} not found"
                    )
            else:
                item_category = None

            brand = get_or_create_brand(data.get("brand_guid"))

            name = data.get("name", "")
            product_defaults = {
                "brand": brand,
                "product_item_category": item_category,
                "name": name,
                "name_uz": data.get("name_uz") or name,
                "name_en": data.get("name_en") or name,
                "description": data.get("description", ""),
                "description_uz": data.get("description_uz", ""),
                "description_en": data.get("description_en", ""),
                "price": data.get("price", 0.0),
                "unit": data.get("unit", "pcs"),
                "quantity": data.get("quantity", 0),
                "discount_price": data.get("discount_price"),
                "discount": data.get("discount"),
                "is_active": data.get("is_active", True),
                "vendor_code": data.get("vendor_code", ""),
                "barcode": data.get("barcode", ""),
            }

            product_guid = data.get("product_guid")
            created = True
            if product_guid:
                product, created = Product.objects.update_or_create(
                    guid=product_guid,
                    defaults=product_defaults,
                )
            else:
                product = Product.objects.create(**product_defaults)

            filter_data = {}
            char_instances = []

            for char_data in data.get("characteristics", []):
                char_name = char_data.get("name_ru") or char_data.get("name", "")
                char_value = char_data.get("value_ru") or char_data.get("value", "")
                char_unit = char_data.get("unit_ru") or char_data.get("unit", "")

                if char_name and char_value:
                    key = make_filter_key(char_name)

                    schema, _ = ProductItemCategoryFilterSchema.objects.get_or_create(
                        item_category=item_category,
                        key=key,
                        defaults={
                            "source_name_ru": char_name,
                            "label": char_name,
                            "unit": char_unit,
                        }
                    ) if item_category else (None, False)

                    if schema:
                        detected_type = detect_filter_type(schema, char_value, char_unit, item_category)
                        if detected_type != schema.type and not schema.type_locked:
                            schema.type = detected_type
                            schema.save(update_fields=["type"])

                        if schema.type == "range":
                            numeric_val = parse_numeric(char_value)
                            if numeric_val is not None:
                                ProductFilterNumericValue.objects.update_or_create(
                                    product=product, schema=schema,
                                    defaults={"value": numeric_val}
                                )
                        else:
                            filter_data[key] = slugify(char_value, allow_unicode=True) or char_value

                char_instances.append(ProductCharacteristics(
                    product=product,
                    name=char_name,
                    name_uz=char_data.get("name_uz", char_name),
                    name_en=char_data.get("name_en", char_name),
                    value=char_value,
                    value_uz=char_data.get("value_uz", char_value),
                    value_en=char_data.get("value_en", char_value),
                    unit=char_unit,
                ))

            ProductCharacteristics.objects.bulk_create(char_instances)

            for img_base64 in data.get("images_base64", []):
                content_file = decode_base64_image(img_base64)
                ProductImage.objects.create(
                    product=product,
                    image=content_file
                )

            product.filter_data = filter_data
            product.save(update_fields=["filter_data"])

        return Response(
            data={
                "result": {
                    "product_id": product.id,
                    "name": product.name,
                    "created": created if product_guid else True,
                },
                "ok": True,
            },
            status=status.HTTP_201_CREATED,
        )
