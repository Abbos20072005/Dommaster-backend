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
    ProductCategory, ProductSubCategory, ProductItemCategory,
    Brand, ProductUnit, ProductItemCategoryFilterSchema, ProductFilterNumericValue,
    ProductRemaining,
)
from base.models import MarketBranch, BRANCH_TYPE_CHOICES

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


def get_or_create_brand(code):
    if not code:
        return None
    brand = Brand.objects.filter(code=code).first()
    if brand:
        return brand
    brand = Brand.objects.create(
        name=code,
        name_uz=code,
        name_en=code,
        code=code,
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
        existing_count = ProductFilterNumericValue.objects.filter(schema=schema).count()
        if existing_count > 20:
            unique_count = ProductFilterNumericValue.objects.filter(
                schema=schema
            ).values("value").distinct().count()
            if unique_count <= 10:
                return "multiselect"
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


class UnitNestedSerializer(serializers.Serializer):
    unit_code = serializers.CharField(required=False, allow_blank=True)
    unit_name_uz = serializers.CharField(required=False, allow_blank=True)
    unit_name_ru = serializers.CharField(required=False, allow_blank=True)
    unit_name_en = serializers.CharField(required=False, allow_blank=True)
    unit_namefull_uz = serializers.CharField(required=False, allow_blank=True)
    unit_namefull_ru = serializers.CharField(required=False, allow_blank=True)
    unit_namefull_en = serializers.CharField(required=False, allow_blank=True)


class BrandNestedSerializer(serializers.Serializer):
    brand_code = serializers.CharField(required=False, allow_blank=True)
    brand_name_uz = serializers.CharField(required=False, allow_blank=True)
    brand_name_ru = serializers.CharField(required=False, allow_blank=True)
    brand_name_en = serializers.CharField(required=False, allow_blank=True)
    image_base64 = serializers.CharField(required=False, allow_blank=True)


class CategoryNestedSerializer(serializers.Serializer):
    category_code = serializers.CharField(required=False, allow_blank=True)
    category_name_uz = serializers.CharField(required=False, allow_blank=True)
    category_name_ru = serializers.CharField(required=False, allow_blank=True)
    category_name_en = serializers.CharField(required=False, allow_blank=True)
    image_base64 = serializers.CharField(required=False, allow_blank=True)
    icon_base64 = serializers.CharField(required=False, allow_blank=True)


class SubCategoryNestedSerializer(serializers.Serializer):
    category_code = serializers.CharField(required=False, allow_blank=True)
    subcategory_code = serializers.CharField(required=False, allow_blank=True)
    subcategory_name_uz = serializers.CharField(required=False, allow_blank=True)
    subcategory_name_ru = serializers.CharField(required=False, allow_blank=True)
    subcategory_name_en = serializers.CharField(required=False, allow_blank=True)
    image_base64 = serializers.CharField(required=False, allow_blank=True)


class ItemCategoryNestedSerializer(serializers.Serializer):
    subcategory_code = serializers.CharField(required=False, allow_blank=True)
    itemcategory_code = serializers.CharField(required=False, allow_blank=True)
    itemcategory_name_uz = serializers.CharField(required=False, allow_blank=True)
    itemcategory_name_ru = serializers.CharField(required=False, allow_blank=True)
    itemcategory_name_en = serializers.CharField(required=False, allow_blank=True)
    image_base64 = serializers.CharField(required=False, allow_blank=True)


class CharacteristicNestedSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True)
    value = serializers.CharField(required=False, allow_blank=True)
    unit = serializers.CharField(required=False, allow_blank=True)


class OneCProductInputSerializer(serializers.Serializer):
    api_key = serializers.CharField(required=True, write_only=True)
    product_code = serializers.CharField(required=False, allow_blank=True)
    product_name_uz = serializers.CharField(required=False, allow_blank=True)
    product_name_ru = serializers.CharField(required=False, allow_blank=True)
    product_name_en = serializers.CharField(required=False, allow_blank=True)
    description_uz = serializers.CharField(required=False, allow_blank=True)
    description_ru = serializers.CharField(required=False, allow_blank=True)
    description_en = serializers.CharField(required=False, allow_blank=True)
    unit = UnitNestedSerializer(required=False)
    brand = BrandNestedSerializer(required=False)
    category = CategoryNestedSerializer(required=False)
    subcategory = SubCategoryNestedSerializer(required=False)
    itemcategory = ItemCategoryNestedSerializer(required=False)
    barcode = serializers.CharField(required=False, allow_blank=True)
    articul_code = serializers.CharField(required=False, allow_blank=True)
    characteristics = serializers.ListField(child=serializers.DictField(), required=False)
    images_base64 = serializers.ListField(child=serializers.CharField(), required=False)
    is_active = serializers.BooleanField(default=True)
    is_active = serializers.BooleanField(default=True)


class OneCBrandInputSerializer(serializers.Serializer):
    api_key = serializers.CharField(required=True, write_only=True)
    brand_code = serializers.CharField(required=False, allow_blank=True)
    brand_name_uz = serializers.CharField(required=False, allow_blank=True)
    brand_name_ru = serializers.CharField(required=False, allow_blank=True)
    brand_name_en = serializers.CharField(required=False, allow_blank=True)
    image_base64 = serializers.CharField(required=True)


class OneCCategoryInputSerializer(serializers.Serializer):
    api_key = serializers.CharField(required=True, write_only=True)
    category_code = serializers.CharField(required=False, allow_blank=True)
    category_name_uz = serializers.CharField(required=False, allow_blank=True)
    category_name_ru = serializers.CharField(required=False, allow_blank=True)
    category_name_en = serializers.CharField(required=False, allow_blank=True)
    image_base64 = serializers.CharField(required=True)
    icon_base64 = serializers.CharField(required=False, allow_blank=True)


class OneCSubCategoryInputSerializer(serializers.Serializer):
    api_key = serializers.CharField(required=True, write_only=True)
    category_code = serializers.CharField(required=True)
    subcategory_code = serializers.CharField(required=False, allow_blank=True)
    subcategory_name_uz = serializers.CharField(required=False, allow_blank=True)
    subcategory_name_ru = serializers.CharField(required=False, allow_blank=True)
    subcategory_name_en = serializers.CharField(required=False, allow_blank=True)
    image_base64 = serializers.CharField(required=True)


class OneCItemCategoryInputSerializer(serializers.Serializer):
    api_key = serializers.CharField(required=True, write_only=True)
    subcategory_code = serializers.CharField(required=True)
    itemcategory_code = serializers.CharField(required=False, allow_blank=True)
    itemcategory_name_uz = serializers.CharField(required=False, allow_blank=True)
    itemcategory_name_ru = serializers.CharField(required=False, allow_blank=True)
    itemcategory_name_en = serializers.CharField(required=False, allow_blank=True)
    image_base64 = serializers.CharField(required=True)


class OneCUnitInputSerializer(serializers.Serializer):
    api_key = serializers.CharField(required=True, write_only=True)
    unit_code = serializers.CharField(required=True)
    unit_name_uz = serializers.CharField(required=False, allow_blank=True)
    unit_name_ru = serializers.CharField(required=False, allow_blank=True)
    unit_name_en = serializers.CharField(required=False, allow_blank=True)
    unit_namefull_uz = serializers.CharField(required=False, allow_blank=True)
    unit_namefull_ru = serializers.CharField(required=False, allow_blank=True)
    unit_namefull_en = serializers.CharField(required=False, allow_blank=True)


class PriceListItemNestedSerializer(serializers.Serializer):
    price_id = serializers.CharField(required=False, allow_blank=True)
    price_code = serializers.CharField(required=False, allow_blank=True)
    price_name = serializers.CharField(required=False, allow_blank=True)


class PriceProductNestedSerializer(serializers.Serializer):
    product_code = serializers.CharField(required=False, allow_blank=True)
    product_price = serializers.CharField(required=False, allow_blank=True)
    discount_precent = serializers.CharField(required=False, allow_blank=True)
    discount_price = serializers.CharField(required=False, allow_blank=True)


class OneCPriceListInputSerializer(serializers.Serializer):
    api_key = serializers.CharField(required=True, write_only=True)
    date = serializers.CharField(required=False, allow_blank=True)
    price = PriceListItemNestedSerializer(required=False, many=True)
    price_list = PriceListItemNestedSerializer(required=False, many=True)
    products = PriceProductNestedSerializer(required=False, many=True)


class OneCWarehouseInputSerializer(serializers.Serializer):
    api_key = serializers.CharField(required=True, write_only=True)
    warehouse_code = serializers.CharField(required=True)
    warehouse_name = serializers.CharField(required=True)
    type = serializers.IntegerField(required=True)
    location_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    address = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)
    working_hours = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    phone_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    image_base64 = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    is_active = serializers.BooleanField(required=False)
    position = serializers.IntegerField(required=False)

    def validate_type(self, value):
        if value not in dict(BRANCH_TYPE_CHOICES):
            raise serializers.ValidationError(
                f"type must be one of {list(dict(BRANCH_TYPE_CHOICES).keys())}"
            )
        return value


class OneCRemainingProductNestedSerializer(serializers.Serializer):
    product_code = serializers.CharField(required=True)
    product_remaining = serializers.FloatField(required=True, min_value=0.0)


class OneCRemainingInputSerializer(serializers.Serializer):
    api_key = serializers.CharField(required=True, write_only=True)
    warehouse_code = serializers.CharField(required=True)
    products = OneCRemainingProductNestedSerializer(many=True, required=True)


class OneCIntegrationViewSet(ViewSet):
    def _upsert_unit(self, unit_data):
        if not unit_data:
            return None
        code = unit_data.get("unit_code")
        if not code:
            return None
        name_uz = unit_data.get("unit_name_uz", "")
        name_ru = unit_data.get("unit_name_ru") or name_uz
        name_en = unit_data.get("unit_name_en") or name_uz
        unit, _ = ProductUnit.objects.update_or_create(
            unit_code=code,
            defaults={
                "name": name_uz,
                "name_uz": name_uz,
                "name_ru": name_ru,
                "name_en": name_en,
                "name_full_uz": unit_data.get("unit_namefull_uz", ""),
                "name_full_ru": unit_data.get("unit_namefull_ru", ""),
                "name_full_en": unit_data.get("unit_namefull_en", ""),
            }
        )
        return unit

    def _upsert_brand(self, brand_data):
        if not brand_data:
            return None
        code = brand_data.get("brand_code")
        if not code:
            return None
        name_uz = brand_data.get("brand_name_uz", "")
        name_ru = brand_data.get("brand_name_ru") or name_uz
        name_en = brand_data.get("brand_name_en") or name_uz
        brand, _ = Brand.objects.update_or_create(
            code=code,
            defaults={
                "name": name_uz,
                "name_uz": name_uz,
                "name_ru": name_ru,
                "name_en": name_en,
            }
        )
        img = brand_data.get("image_base64")
        if img:
            content_file = decode_base64_image(img)
            brand.image.save(content_file.name, content_file, save=True)
        return brand

    def _upsert_category(self, cat_data):
        if not cat_data:
            return None
        code = cat_data.get("category_code")
        if not code:
            return None
        name_uz = cat_data.get("category_name_uz", "")
        name_ru = cat_data.get("category_name_ru") or name_uz
        name_en = cat_data.get("category_name_en") or name_uz
        cat, _ = ProductCategory.objects.update_or_create(
            code=code,
            defaults={
                "name": name_uz,
                "name_uz": name_uz,
                "name_ru": name_ru,
                "name_en": name_en,
            }
        )
        for field, key in [("image", "image_base64"), ("icon", "icon_base64")]:
            raw = cat_data.get(key)
            if raw:
                content_file = decode_base64_image(raw)
                getattr(cat, field).save(content_file.name, content_file, save=True)
        return cat

    def _upsert_subcategory(self, sub_data, category=None):
        if not sub_data:
            return None
        code = sub_data.get("subcategory_code")
        if not code:
            return None

        category_code = sub_data.get("category_code")
        if category is None and category_code:
            category, _ = ProductCategory.objects.update_or_create(
                code=category_code,
                defaults={
                    "name": category_code,
                    "name_uz": category_code,
                    "name_ru": category_code,
                    "name_en": category_code,
                }
            )

        if category is None:
            raise CustomApiException(error_code=ErrorCodes.INTEGRATION_CATEGORY_NOT_FOUND)

        name_uz = sub_data.get("subcategory_name_uz", "")
        name_ru = sub_data.get("subcategory_name_ru") or name_uz
        name_en = sub_data.get("subcategory_name_en") or name_uz
        sub, _ = ProductSubCategory.objects.update_or_create(
            code=code,
            defaults={
                "product_category": category,
                "name": name_uz,
                "name_uz": name_uz,
                "name_ru": name_ru,
                "name_en": name_en,
            }
        )
        img = sub_data.get("image_base64")
        if img:
            content_file = decode_base64_image(img)
            sub.image.save(content_file.name, content_file, save=True)
        return sub

    def _upsert_itemcategory(self, item_data, subcategory=None):
        if not item_data:
            return None
        code = item_data.get("itemcategory_code")
        if not code:
            return None

        subcategory_code = item_data.get("subcategory_code")
        if subcategory is None and subcategory_code:
            subcategory, _ = ProductSubCategory.objects.update_or_create(
                code=subcategory_code,
                defaults={
                    "name": subcategory_code,
                    "name_uz": subcategory_code,
                    "name_ru": subcategory_code,
                    "name_en": subcategory_code,
                }
            )

        if subcategory is None:
            raise CustomApiException(error_code=ErrorCodes.INTEGRATION_SUB_CATEGORY_NOT_FOUND)

        name_uz = item_data.get("itemcategory_name_uz", "")
        name_ru = item_data.get("itemcategory_name_ru") or name_uz
        name_en = item_data.get("itemcategory_name_en") or name_uz
        item, _ = ProductItemCategory.objects.update_or_create(
            code=code,
            defaults={
                "product_sub_category": subcategory,
                "name": name_uz,
                "name_uz": name_uz,
                "name_ru": name_ru,
                "name_en": name_en,
            }
        )
        img = item_data.get("image_base64")
        if img:
            content_file = decode_base64_image(img)
            item.image.save(content_file.name, content_file, save=True)
        return item

    @swagger_auto_schema(
        operation_summary="1C Product create",
        operation_description="Create product from 1C",
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
            unit = self._upsert_unit(data.get("unit"))
            brand = self._upsert_brand(data.get("brand"))
            category = self._upsert_category(data.get("category"))
            subcategory = self._upsert_subcategory(data.get("subcategory"), category=category)
            item_category = self._upsert_itemcategory(data.get("itemcategory"), subcategory=subcategory)

            name_uz = data.get("product_name_uz", "")
            name_ru = data.get("product_name_ru") or name_uz
            name_en = data.get("product_name_en") or name_uz
            name = name_uz

            description_uz = data.get("description_uz", "")
            description_ru = data.get("description_ru") or description_uz
            description_en = data.get("description_en") or description_uz
            description = description_uz

            unit_label = unit.name if unit else "pcs"

            product_code = data.get("product_code")
            product_defaults = {
                "brand": brand,
                "product_item_category": item_category,
                "name": name,
                "name_uz": name_uz,
                "name_ru": name_ru,
                "name_en": name_en,
                "description": description,
                "description_uz": description_uz,
                "description_ru": description_ru,
                "description_en": description_en,
                "unit": unit_label,
                "is_active": data.get("is_active", True),
                "articul_code": data.get("articul_code", ""),
                "barcode": data.get("barcode", ""),
            }

            created = True
            if product_code:
                product, created = Product.objects.update_or_create(
                    product_code=product_code,
                    defaults=product_defaults,
                )
            else:
                product = Product.objects.create(**product_defaults)

            filter_data = {}
            char_instances = []

            for char_data in data.get("characteristics", []):
                char_name = char_data.get("name", "")
                char_value = char_data.get("value", "")
                char_unit = char_data.get("unit", "")

                if not char_name or not char_value:
                    continue

                key = make_filter_key(char_name)

                schema = None
                if item_category:
                    schema, _ = ProductItemCategoryFilterSchema.objects.get_or_create(
                        item_category=item_category,
                        key=key,
                        defaults={
                            "source_name_ru": char_name,
                            "label": char_name,
                            "unit": char_unit,
                        }
                    )

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
                        filter_data[key] = char_value

                char_instances.append(ProductCharacteristics(
                    product=product,
                    name=char_name,
                    name_uz=char_name,
                    name_en=char_name,
                    value=char_value,
                    value_uz=char_value,
                    value_en=char_value,
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
                    "product_code": product.product_code or product_code,
                    "product_name_uz": product.name_uz,
                    "product_name_ru": product.name_ru,
                    "product_name_en": product.name_en,
                },
                "ok": True,
            },
            status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_summary="1C Brand create",
        operation_description="Create or update brand from 1C",
        request_body=OneCBrandInputSerializer(),
        responses={201: "Brand created"},
        tags=["1C Integration"]
    )
    def brand_create(self, request):
        serializer = OneCBrandInputSerializer(data=request.data)
        if not serializer.is_valid():
            raise CustomApiException(
                error_code=ErrorCodes.INTEGRATION_INVALID_DATA,
                message=serializer.errors
            )

        data = serializer.validated_data

        if data.get("api_key") != INTEGRATION_API_KEY:
            raise CustomApiException(error_code=ErrorCodes.INTEGRATION_API_KEY_INVALID)

        name_uz = data.get("brand_name_uz", "")
        name_ru = data.get("brand_name_ru") or name_uz
        name_en = data.get("brand_name_en") or name_uz
        brand_code = data.get("brand_code")

        with transaction.atomic():
            brand_defaults = {
                "name": name_uz,
                "name_uz": name_uz,
                "name_ru": name_ru,
                "name_en": name_en,
            }

            if brand_code:
                brand, created = Brand.objects.update_or_create(
                    code=brand_code,
                    defaults=brand_defaults,
                )
            else:
                brand = Brand.objects.create(**brand_defaults)
                created = True

            image_base64 = data.get("image_base64")
            if image_base64:
                content_file = decode_base64_image(image_base64)
                brand.image.save(content_file.name, content_file, save=True)

        return Response(
            data={
                "result": {
                    "brand_code": brand.code or brand_code,
                    "name_uz": brand.name_uz,
                    "name_ru": brand.name_ru,
                    "name_en": brand.name_en,
                },
                "ok": True,
            },
            status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_summary="1C Category create",
        operation_description="Create category from 1C",
        request_body=OneCCategoryInputSerializer(),
        responses={201: "Category created"},
        tags=["1C Integration"]
    )
    def category_create(self, request):
        serializer = OneCCategoryInputSerializer(data=request.data)
        if not serializer.is_valid():
            raise CustomApiException(
                error_code=ErrorCodes.INTEGRATION_INVALID_DATA,
                message=serializer.errors
            )

        data = serializer.validated_data

        if data.get("api_key") != INTEGRATION_API_KEY:
            raise CustomApiException(error_code=ErrorCodes.INTEGRATION_API_KEY_INVALID)

        name_uz = data.get("category_name_uz", "")
        name_ru = data.get("category_name_ru") or name_uz
        name_en = data.get("category_name_en") or name_uz
        category_code = data.get("category_code")

        with transaction.atomic():
            defaults = {
                "name": name_uz,
                "name_uz": name_uz,
                "name_ru": name_ru,
                "name_en": name_en,
            }

            if category_code:
                category, created = ProductCategory.objects.update_or_create(
                    code=category_code,
                    defaults=defaults,
                )
            else:
                category = ProductCategory.objects.create(**defaults)
                created = True

            for field, base64_key in [("image", "image_base64"), ("icon", "icon_base64")]:
                raw = data.get(base64_key)
                if raw:
                    content_file = decode_base64_image(raw)
                    getattr(category, field).save(content_file.name, content_file, save=True)

        return Response(
            data={
                "result": {
                    "category_code": category.code or category_code,
                    "name_uz": category.name_uz,
                    "name_ru": category.name_ru,
                    "name_en": category.name_en,
                },
                "ok": True,
            },
            status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_summary="1C Sub-category create",
        operation_description="Create sub-category from 1C",
        request_body=OneCSubCategoryInputSerializer(),
        responses={201: "Sub-category created"},
        tags=["1C Integration"]
    )
    def sub_category_create(self, request):
        serializer = OneCSubCategoryInputSerializer(data=request.data)
        if not serializer.is_valid():
            raise CustomApiException(
                error_code=ErrorCodes.INTEGRATION_INVALID_DATA,
                message=serializer.errors
            )

        data = serializer.validated_data

        if data.get("api_key") != INTEGRATION_API_KEY:
            raise CustomApiException(error_code=ErrorCodes.INTEGRATION_API_KEY_INVALID)

        name_uz = data.get("subcategory_name_uz", "")
        name_ru = data.get("subcategory_name_ru") or name_uz
        name_en = data.get("subcategory_name_en") or name_uz
        subcategory_code = data.get("subcategory_code")

        category_code = data.get("category_code")
        product_category = ProductCategory.objects.filter(code=category_code).first() if category_code else None
        if not product_category:
            raise CustomApiException(error_code=ErrorCodes.INTEGRATION_CATEGORY_NOT_FOUND)

        with transaction.atomic():
            defaults = {
                "product_category": product_category,
                "name": name_uz,
                "name_uz": name_uz,
                "name_ru": name_ru,
                "name_en": name_en,
            }

            if subcategory_code:
                sub_category, created = ProductSubCategory.objects.update_or_create(
                    code=subcategory_code,
                    defaults=defaults,
                )
            else:
                sub_category = ProductSubCategory.objects.create(**defaults)
                created = True

            image_base64 = data.get("image_base64")
            if image_base64:
                content_file = decode_base64_image(image_base64)
                sub_category.image.save(content_file.name, content_file, save=True)

        return Response(
            data={
                "result": {
                    "subcategory_code": sub_category.code or subcategory_code,
                    "name_uz": sub_category.name_uz,
                    "name_ru": sub_category.name_ru,
                    "name_en": sub_category.name_en,
                },
                "ok": True,
            },
            status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_summary="1C Item-category create",
        operation_description="Create item-category from 1C",
        request_body=OneCItemCategoryInputSerializer(),
        responses={201: "Item-category created"},
        tags=["1C Integration"]
    )
    def item_category_create(self, request):
        serializer = OneCItemCategoryInputSerializer(data=request.data)
        if not serializer.is_valid():
            raise CustomApiException(
                error_code=ErrorCodes.INTEGRATION_INVALID_DATA,
                message=serializer.errors
            )

        data = serializer.validated_data

        if data.get("api_key") != INTEGRATION_API_KEY:
            raise CustomApiException(error_code=ErrorCodes.INTEGRATION_API_KEY_INVALID)

        name_uz = data.get("itemcategory_name_uz", "")
        name_ru = data.get("itemcategory_name_ru") or name_uz
        name_en = data.get("itemcategory_name_en") or name_uz
        itemcategory_code = data.get("itemcategory_code")

        subcategory_code = data.get("subcategory_code")
        product_sub_category = ProductSubCategory.objects.filter(code=subcategory_code).first() if subcategory_code else None
        if not product_sub_category:
            raise CustomApiException(error_code=ErrorCodes.INTEGRATION_SUB_CATEGORY_NOT_FOUND)

        with transaction.atomic():
            defaults = {
                "product_sub_category": product_sub_category,
                "name": name_uz,
                "name_uz": name_uz,
                "name_ru": name_ru,
                "name_en": name_en,
            }

            if itemcategory_code:
                item_category, created = ProductItemCategory.objects.update_or_create(
                    code=itemcategory_code,
                    defaults=defaults,
                )
            else:
                item_category = ProductItemCategory.objects.create(**defaults)
                created = True

            image_base64 = data.get("image_base64")
            if image_base64:
                content_file = decode_base64_image(image_base64)
                item_category.image.save(content_file.name, content_file, save=True)

        return Response(
            data={
                "result": {
                    "itemcategory_code": item_category.code or itemcategory_code,
                    "name_uz": item_category.name_uz,
                    "name_ru": item_category.name_ru,
                    "name_en": item_category.name_en,
                },
                "ok": True,
            },
            status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_summary="1C Unit create",
        operation_description="Create unit from 1C",
        request_body=OneCUnitInputSerializer(),
        responses={201: "Unit created"},
        tags=["1C Integration"]
    )
    def unit_create(self, request):
        serializer = OneCUnitInputSerializer(data=request.data)
        if not serializer.is_valid():
            raise CustomApiException(
                error_code=ErrorCodes.INTEGRATION_INVALID_DATA,
                message=serializer.errors
            )

        data = serializer.validated_data

        if data.get("api_key") != INTEGRATION_API_KEY:
            raise CustomApiException(error_code=ErrorCodes.INTEGRATION_API_KEY_INVALID)

        name_uz = data.get("unit_name_uz", "")
        name_ru = data.get("unit_name_ru") or name_uz
        name_en = data.get("unit_name_en") or name_uz

        with transaction.atomic():
            unit, created = ProductUnit.objects.update_or_create(
                unit_code=data.get("unit_code"),
                defaults={
                    "name": name_uz,
                    "name_uz": name_uz,
                    "name_ru": name_ru,
                    "name_en": name_en,
                    "name_full_uz": data.get("unit_namefull_uz", ""),
                    "name_full_ru": data.get("unit_namefull_ru", ""),
                    "name_full_en": data.get("unit_namefull_en", ""),
                }
            )

        return Response(
            data={
                "result": {
                    "unit_code": unit.unit_code,
                    "unit_name_uz": unit.name_uz,
                    "unit_name_ru": unit.name_ru,
                    "unit_name_en": unit.name_en,
                    "unit_namefull_uz": unit.name_full_uz,
                    "unit_namefull_ru": unit.name_full_ru,
                    "unit_namefull_en": unit.name_full_en,
                },
                "ok": True,
            },
            status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_summary="1C Price list create",
        operation_description="Apply price list from 1C. Only product_code, product_price, discount_precent "
                              "and discount_price are used to update the product price and discount; "
                              "date and price list info are accepted but ignored.",
        request_body=OneCPriceListInputSerializer(),
        responses={200: "Prices updated"},
        tags=["1C Integration"]
    )
    def price_list_create(self, request):
        serializer = OneCPriceListInputSerializer(data=request.data)
        if not serializer.is_valid():
            raise CustomApiException(
                error_code=ErrorCodes.INTEGRATION_INVALID_DATA,
                message=serializer.errors
            )

        data = serializer.validated_data

        if data.get("api_key") != INTEGRATION_API_KEY:
            raise CustomApiException(error_code=ErrorCodes.INTEGRATION_API_KEY_INVALID)

        date = data.get("date")
        price_list = data.get("price") or data.get("price_list") or []
        products = data.get("products", [])

        product_updates = {}
        for item in products:
            code = (item.get("product_code") or "").strip()
            raw_price = item.get("product_price")
            if not code or raw_price in (None, ""):
                continue
            price = parse_numeric(raw_price)
            if price is None:
                continue
            updates = {"price": price}
            raw_discount_precent = item.get("discount_precent")
            raw_discount_price = item.get("discount_price")
            if raw_discount_precent not in (None, ""):
                discount_precent = parse_numeric(raw_discount_precent)
                if discount_precent is not None:
                    updates["discount"] = int(discount_precent)
            if raw_discount_price not in (None, ""):
                discount_price = parse_numeric(raw_discount_price)
                if discount_price is not None:
                    updates["discount_price"] = discount_price
            product_updates[code] = updates

        if not product_updates:
            raise CustomApiException(
                error_code=ErrorCodes.INTEGRATION_INVALID_DATA,
                message="products: no valid product_code/product_price entries"
            )

        updated_count = 0
        not_found = []

        with transaction.atomic():
            for code, updates in product_updates.items():
                updated = Product.objects.filter(product_code=code).update(**updates)
                if updated:
                    updated_count += 1
                else:
                    not_found.append(code)

        return Response(
            data={
                "result": {
                    "date": date,
                    "price_list_count": len(price_list),
                    "products_count": len(products),
                    "updated_count": updated_count,
                    "not_found_codes": not_found,
                },
                "ok": True,
            },
            status=status.HTTP_200_OK,
        )

    @swagger_auto_schema(
        operation_summary="1C Warehouse create",
        operation_description="Create or update warehouse/branch from 1C. "
                              "type: 0 - Showroom, 1 - Market, 2 - Warehouse",
        request_body=OneCWarehouseInputSerializer(),
        responses={201: "Warehouse created"},
        tags=["1C Integration"]
    )
    def warehouse_create(self, request):
        serializer = OneCWarehouseInputSerializer(data=request.data)
        if not serializer.is_valid():
            raise CustomApiException(
                error_code=ErrorCodes.INTEGRATION_INVALID_DATA,
                message=serializer.errors
            )

        data = serializer.validated_data

        if data.get("api_key") != INTEGRATION_API_KEY:
            raise CustomApiException(error_code=ErrorCodes.INTEGRATION_API_KEY_INVALID)

        warehouse_code = data.get("warehouse_code")
        warehouse_name = data.get("warehouse_name")

        branch_defaults = {
            "name": warehouse_name,
            "name_uz": warehouse_name,
            "name_ru": warehouse_name,
            "name_en": warehouse_name,
            "branch_type": data.get("type"),
        }
        optional_fields = (
            "location_name", "address", "latitude", "longitude",
            "working_hours", "description", "phone_number", "is_active", "position"
        )
        for field in optional_fields:
            if field in data:
                branch_defaults[field] = data[field]

        with transaction.atomic():
            branch, created = MarketBranch.objects.update_or_create(
                code=warehouse_code,
                defaults=branch_defaults,
            )

            image_base64 = data.get("image_base64")
            if image_base64:
                content_file = decode_base64_image(image_base64)
                branch.image.save(content_file.name, content_file, save=True)

        return Response(
            data={
                "result": {
                    "warehouse_code": branch.code,
                    "warehouse_name": branch.name,
                    "type": dict(BRANCH_TYPE_CHOICES).get(branch.branch_type),
                    "location_name": branch.location_name,
                    "address": branch.address,
                    "latitude": branch.latitude,
                    "longitude": branch.longitude,
                    "working_hours": branch.working_hours,
                    "description": branch.description,
                    "phone_number": branch.phone_number,
                    "is_active": branch.is_active,
                    "position": branch.position,
                },
                "ok": True,
            },
            status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_summary="1C Product remaining create",
        operation_description="Create or update product remainings for a warehouse from 1C",
        request_body=OneCRemainingInputSerializer(),
        responses={201: "Product remainings created"},
        tags=["1C Integration"]
    )
    def remaining_create(self, request):
        serializer = OneCRemainingInputSerializer(data=request.data)
        if not serializer.is_valid():
            raise CustomApiException(
                error_code=ErrorCodes.INTEGRATION_INVALID_DATA,
                message=serializer.errors
            )

        data = serializer.validated_data

        if data.get("api_key") != INTEGRATION_API_KEY:
            raise CustomApiException(error_code=ErrorCodes.INTEGRATION_API_KEY_INVALID)

        branch = MarketBranch.objects.filter(code=data.get("warehouse_code")).first()
        if not branch:
            raise CustomApiException(error_code=ErrorCodes.INTEGRATION_WAREHOUSE_NOT_FOUND)

        products_data = data.get("products")
        requested_codes = [item.get("product_code") for item in products_data]
        remaining_by_code = {item.get("product_code"): item.get("product_remaining") for item in products_data}

        products = Product.objects.filter(product_code__in=requested_codes).only("id", "product_code")
        products_map = {product.product_code: product for product in products}

        if not products_map:
            raise CustomApiException(error_code=ErrorCodes.INTEGRATION_PRODUCT_NOT_FOUND)

        skipped_products = list(dict.fromkeys(code for code in requested_codes if code not in products_map))

        existing_product_ids = set(
            ProductRemaining.objects.filter(branch=branch, product_id__in=products.values("id"))
            .values_list("product_id", flat=True)
        )

        ProductRemaining.objects.bulk_create(
            [
                ProductRemaining(branch=branch, product=product, quantity=remaining_by_code[product_code])
                for product_code, product in products_map.items()
            ],
            update_conflicts=True,
            unique_fields=["branch", "product"],
            update_fields=["quantity"],
            batch_size=500,
        )

        any_created = bool({product.id for product in products_map.values()} - existing_product_ids)

        result = [
            {
                "warehouse_code": branch.code,
                "product_code": product_code,
                "product_remaining": quantity,
            }
            for product_code, quantity in remaining_by_code.items()
            if product_code in products_map
        ]

        return Response(
            data={
                "result": result,
                "skipped_products": skipped_products,
                "ok": True,
            },
            status=status.HTTP_201_CREATED if any_created else status.HTTP_200_OK,
        )
