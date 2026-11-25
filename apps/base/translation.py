from .models import News, Banner, Video, Promocodes, AboutUs, MarketBranch, Notification, FaqItem
from modeltranslation.translator import translator, TranslationOptions


class AboutUsOption(TranslationOptions):
    fields = ("description",)


class PromocodesOption(TranslationOptions):
    fields = ("name",)


class NewsOption(TranslationOptions):
    fields = ("title", "description")


class BannerOption(TranslationOptions):
    # images carry text, so each language has its own pair (desktop + mobile); an empty uz one falls back to ru
    fields = ("title", "desktop_image", "mobile_image")


class VideoOption(TranslationOptions):
    fields = ("name",)


class MarketBranchOption(TranslationOptions):
    fields = ("name", "location_name", "description", "landmark", "address")


class NotificationOption(TranslationOptions):
    fields = ("title", "description")


translator.register(AboutUs, AboutUsOption)
translator.register(Notification, NotificationOption)
translator.register(Promocodes, PromocodesOption)
translator.register(Video, VideoOption)
translator.register(Banner, BannerOption)
translator.register(News, NewsOption)
translator.register(MarketBranch, MarketBranchOption)


class FaqItemOption(TranslationOptions):
    fields = ("question", "answer")


translator.register(FaqItem, FaqItemOption)
