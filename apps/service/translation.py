from modeltranslation.translator import translator, TranslationOptions
from .models import Product, ProductImage, Service, ProductCharacteristics, AddsBrands, Brand, ProductCategory, \
    ProductSubCategory, ProductItemCategory, ProductVariantGroup, ProductVariantItem, \
    ProductItemCategoryFilterSchema, ProductUnit, ProductBadge, ProductAttribute, ProductAttributeOption, \
    ProductAttributeValue, HomeBlock, FilterPage


class ProductItemCategoryOption(TranslationOptions):
    fields = ("name", "slug", "meta_title", "meta_description", "image_alt", "description")


class ProductSubCategoryOption(TranslationOptions):
    fields = ("name", "slug", "meta_title", "meta_description", "image_alt", "description")


class ProductCategoryOption(TranslationOptions):
    fields = ("name", "slug", "meta_title", "meta_description", "image_alt", "description")


class ProductTranslationOption(TranslationOptions):
    fields = ("name", "slug", "short_description", "description", "meta_title", "meta_description")


class ProductImageOption(TranslationOptions):
    fields = ("alt",)


class ServiceTranslationOption(TranslationOptions):
    fields = ("name", "description")


class ProductCharacteristicsOption(TranslationOptions):
    fields = ("name", "unit", "value")


class AddsBrandsOption(TranslationOptions):
    fields = ("name", "title", "description")


class BrandOption(TranslationOptions):
    fields = ("name", "description", "slug", "meta_title", "meta_description", "image_alt")


class ProductBadgeOption(TranslationOptions):
    fields = ("name",)


class ProductAttributeTranslationOption(TranslationOptions):
    fields = ("name",)


class ProductAttributeOptionTranslationOption(TranslationOptions):
    fields = ("value",)


class ProductAttributeValueTranslationOption(TranslationOptions):
    fields = ("value",)


translator.register(ProductItemCategory, ProductItemCategoryOption)
translator.register(ProductSubCategory, ProductSubCategoryOption)
translator.register(ProductCategory, ProductCategoryOption)
translator.register(Brand, BrandOption)
translator.register(ProductBadge, ProductBadgeOption)
translator.register(ProductAttribute, ProductAttributeTranslationOption)
translator.register(ProductAttributeOption, ProductAttributeOptionTranslationOption)
translator.register(ProductAttributeValue, ProductAttributeValueTranslationOption)
translator.register(AddsBrands, AddsBrandsOption)
translator.register(ProductCharacteristics, ProductCharacteristicsOption)
translator.register(Product, ProductTranslationOption)
translator.register(ProductImage, ProductImageOption)
translator.register(Service, ServiceTranslationOption)


class ProductVariantGroupOption(TranslationOptions):
    fields = ("name",)

class ProductVariantItemOption(TranslationOptions):
    fields = ("display_value",)

translator.register(ProductVariantGroup, ProductVariantGroupOption)
translator.register(ProductVariantItem, ProductVariantItemOption)


class ProductItemCategoryFilterSchemaOption(TranslationOptions):
    fields = ("label",)


translator.register(ProductItemCategoryFilterSchema, ProductItemCategoryFilterSchemaOption)


class ProductUnitOption(TranslationOptions):
    fields = ("name",)


translator.register(ProductUnit, ProductUnitOption)


class HomeBlockOption(TranslationOptions):
    fields = ("title",)


translator.register(HomeBlock, HomeBlockOption)


class FilterPageOption(TranslationOptions):
    fields = ("keyword", "title", "meta_title", "meta_description", "text")


translator.register(FilterPage, FilterPageOption)
