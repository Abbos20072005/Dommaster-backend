from rest_framework import serializers
from apps.service.models import ProductCategory, ProductSubCategory, ProductItemCategory
from utils.admin_serializers import RelationSerializer


class ProductCategoryShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ("id", "name")


class ProductSubCategoryShortSerializer(serializers.ModelSerializer):
    product_category = ProductCategoryShortSerializer(read_only=True)

    class Meta:
        model = ProductSubCategory
        fields = ("id", "name", "product_category")


class ProductItemCategorySerializer(RelationSerializer):
    product_sub_category = ProductSubCategoryShortSerializer(read_only=True)

    class Meta:
        model = ProductItemCategory
        fields = ("id", "name", "product_sub_category")


class CategoryParentSerializer(RelationSerializer):
    class Meta:
        model = ProductCategory
        fields = ("id", "name")


class SubCategoryParentSerializer(RelationSerializer):
    product_category = ProductCategoryShortSerializer(read_only=True)

    class Meta:
        model = ProductSubCategory
        fields = ("id", "name", "product_category")


class CategoryBaseSerializer(serializers.ModelSerializer):
    products_count = serializers.IntegerField(read_only=True, default=0)

    def validate_code(self, value):
        # unique column: store empty codes as NULL
        return value or None


class ProductCategorySerializer(CategoryBaseSerializer):
    children_count = serializers.IntegerField(read_only=True, default=0, help_text="Sub categories")

    class Meta:
        model = ProductCategory
        fields = ("id", "name", "name_uz", "name_ru", "name_en", "code", "icon", "image", "position",
                  "is_active", "children_count", "products_count", "created_at", "updated_at")
        read_only_fields = ("name", "created_at", "updated_at")
        # ru is the default (fallback) language
        extra_kwargs = {"name_ru": {"required": True, "allow_null": False, "allow_blank": False}}


class ProductSubCategoryAdminSerializer(CategoryBaseSerializer):
    product_category = CategoryParentSerializer()
    children_count = serializers.IntegerField(read_only=True, default=0, help_text="Item categories")

    class Meta:
        model = ProductSubCategory
        fields = ("id", "name", "name_uz", "name_ru", "name_en", "code", "product_category", "image",
                  "is_active", "children_count", "products_count", "created_at", "updated_at")
        read_only_fields = ("name", "created_at", "updated_at")
        extra_kwargs = {"name_ru": {"required": True, "allow_null": False, "allow_blank": False}}


class ProductItemCategoryAdminSerializer(CategoryBaseSerializer):
    product_sub_category = SubCategoryParentSerializer()

    class Meta:
        model = ProductItemCategory
        fields = ("id", "name", "name_uz", "name_ru", "name_en", "code", "product_sub_category", "image",
                  "is_active", "products_count", "created_at", "updated_at")
        read_only_fields = ("name", "created_at", "updated_at")
        extra_kwargs = {"name_ru": {"required": True, "allow_null": False, "allow_blank": False}}
