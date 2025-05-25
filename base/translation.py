from .models import News, Banner, Video, Promocodes, AboutUs
from modeltranslation.translator import translator, TranslationOptions


class AboutUsOption(TranslationOptions):
    fields = ("description",)


class PromocodesOption(TranslationOptions):
    fields = ("name",)


class NewsOption(TranslationOptions):
    fields = ("title", "description")


class BannerOption(TranslationOptions):
    fields = ("title",)


class VideoOption(TranslationOptions):
    fields = ("name",)


translator.register(AboutUs, AboutUsOption)
translator.register(Promocodes, PromocodesOption)
translator.register(Video, VideoOption)
translator.register(Banner, BannerOption)
translator.register(News, NewsOption)
