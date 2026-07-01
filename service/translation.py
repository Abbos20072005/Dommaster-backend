from modeltranslation.translator import translator, TranslationOptions
from .models import Product, Service, ProductCharacteristics, AddsBrands, Brand, ProductCategory, ProductSubCategory, \
    ProductItemCategory, ProductVariantGroup, ProductVariantItem, \
    ProductItemCategoryFilterSchema


class ProductItemCategoryOption(TranslationOptions):
    fields = ("name",)


class ProductSubCategoryOption(TranslationOptions):
    fields = ("name",)


class ProductCategoryOption(TranslationOptions):
    fields = ("name",)


class ProductTranslationOption(TranslationOptions):
    fields = ("name", "description")


class ServiceTranslationOption(TranslationOptions):
    fields = ("name", "description")


class ProductCharacteristicsOption(TranslationOptions):
    fields = ("name", "unit", "value")


class AddsBrandsOption(TranslationOptions):
    fields = ("name", "title", "description")


class BrandOption(TranslationOptions):
    fields = ("name",)


translator.register(ProductItemCategory, ProductItemCategoryOption)
translator.register(ProductSubCategory, ProductSubCategoryOption)
translator.register(ProductCategory, ProductCategoryOption)
translator.register(Brand, BrandOption)
translator.register(AddsBrands, AddsBrandsOption)
translator.register(ProductCharacteristics, ProductCharacteristicsOption)
translator.register(Product, ProductTranslationOption)
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
