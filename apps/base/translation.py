from .models import News, Banner, Video, Promocodes, AboutUs, MarketBranch, Notification
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


class MarketBranchOption(TranslationOptions):
    fields = ("name", "location_name", "description")


class NotificationOption(TranslationOptions):
    fields = ("title", "description")


translator.register(AboutUs, AboutUsOption)
translator.register(Notification, NotificationOption)
translator.register(Promocodes, PromocodesOption)
translator.register(Video, VideoOption)
translator.register(Banner, BannerOption)
translator.register(News, NewsOption)
translator.register(MarketBranch, MarketBranchOption)
