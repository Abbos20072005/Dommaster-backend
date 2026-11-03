from django.core.files.storage import default_storage
from rest_framework import serializers

from apps.service import funnel
from apps.service.models import Product
from .dashboard import DateRangeQuerySerializer


class ProductFunnelQuerySerializer(DateRangeQuerySerializer):
    """?days= (default 30, ending today) or ?date_from=&date_to=, plus the channel."""
    channel = serializers.ChoiceField(choices=funnel.CHANNELS, default=funnel.ALL,
                                      help_text="all / site / app (ios + android)")


class ProductFunnelExportQuerySerializer(ProductFunnelQuerySerializer):
    language = serializers.ChoiceField(choices=("ru", "uz"), default="ru",
                                       help_text="Language of the headers and of the product name")


class ProductFunnelRowSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField(help_text="The main (first) image, null = none")
    views = serializers.IntegerField(read_only=True, help_text="product_view events")
    add_to_cart = serializers.IntegerField(read_only=True, help_text="add_to_cart events")
    checkout_start = serializers.IntegerField(read_only=True, help_text="checkout_start events")
    purchases = serializers.IntegerField(
        read_only=True, help_text="Completed orders created in the range with this product, of the site / app")
    incomplete = serializers.IntegerField(read_only=True, help_text="checkout_start - purchases")
    completion_rate = serializers.FloatField(
        read_only=True, allow_null=True, help_text="purchases / checkout_start, %; null when checkout_start is 0")
    other_purchases = serializers.IntegerField(
        read_only=True, help_text="Completed orders without a channel (admin panel, old app); channel=all only")

    class Meta:
        model = Product
        fields = ("id", "name", "articul_code", "image", "views", "add_to_cart", "checkout_start", "purchases",
                  "incomplete", "completion_rate", "other_purchases")

    def get_image(self, product) -> str:
        if not product.image_path:
            return None
        url = default_storage.url(product.image_path)
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url
