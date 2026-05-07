from modeltranslation.translator import translator, TranslationOptions
from .models import Product, Service, ProductCharacteristics, AddsBrands, Brand, ProductCategory, ProductSubCategory, \
    ProductItemCategory, CategoryAttribute, CategoryAttributeValue


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


class CategoryAttributeOption(TranslationOptions):
    fields = ("name",)


class CategoryAttributeValueOption(TranslationOptions):
    fields = ("value",)


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
translator.register(CategoryAttribute, CategoryAttributeOption)
translator.register(CategoryAttributeValue, CategoryAttributeValueOption)
translator.register(Product, ProductTranslationOption)
translator.register(Service, ServiceTranslationOption)
