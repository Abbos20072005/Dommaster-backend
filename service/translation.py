from modeltranslation.translator import translator, TranslationOptions
from .models import Product


class ProductTranslationOption(TranslationOptions):
    fields = ("name", "description")

translator.register(Product, ProductTranslationOption)