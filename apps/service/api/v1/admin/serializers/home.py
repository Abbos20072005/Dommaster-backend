from typing import Optional
from django.db.models import Max
from rest_framework import serializers
from apps.authorization.api.v1.admin.serializers import StaffShortSerializer
from apps.base.models import Banner
from apps.service import home
from apps.service.models import HomeBlock, HomePage, Sale
from utils.admin_serializers import RelationSerializer
from .category import CategoryReorderSerializer
from .product import ProductBadgeShortSerializer

# block type -> the source field it can't live without
REQUIRED_SOURCE = {
    HomeBlock.SLIDER: "banner_placement",
    HomeBlock.BANNER: "banner",
    HomeBlock.BADGE_PRODUCTS: "badge",
    HomeBlock.NEW_PRODUCTS: "days",
    HomeBlock.PAGES: "pages",
}
# block type -> the source fields it uses; the rest are emptied
TYPE_SOURCES = {**{block_type: (field,) for block_type, field in REQUIRED_SOURCE.items()},
                HomeBlock.SALE_PRODUCTS: ("sale",)}
SOURCE_FIELDS = ("banner_placement", "banner", "badge", "sale", "days", "pages")
CHANNEL_FIELDS = ("show_on_site", "show_in_app")


class HomeBlockBannerSerializer(RelationSerializer):
    status = serializers.ChoiceField(choices=Banner.STATUS_CHOICES, read_only=True)

    class Meta:
        model = Banner
        fields = ("id", "title", "placement", "status")


class HomeBlockSaleSerializer(RelationSerializer):
    class Meta:
        model = Sale
        fields = ("id", "name", "is_main", "is_visible")


class HomeBlockPageSerializer(serializers.Serializer):
    title_uz = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    title_ru = serializers.CharField(max_length=255)
    title_en = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    path = serializers.RegexField(r"^/", max_length=255, help_text="Internal path, e.g. /delivery")


class HomeBlockStatusField(serializers.ChoiceField):
    """Not stored: `is_visible` + the display rules of the page."""

    def __init__(self, **kwargs):
        super().__init__(choices=HomeBlock.STATUS_CHOICES, read_only=True, **kwargs)

    def get_attribute(self, block):
        return home.block_status(block, self.context["home_page"], self.parent.get_items_count(block))


class HomeBlockSerializer(serializers.ModelSerializer):
    banner = HomeBlockBannerSerializer(required=False, allow_null=True)
    badge = ProductBadgeShortSerializer(required=False, allow_null=True)
    sale = HomeBlockSaleSerializer(required=False, allow_null=True, help_text="sale_products: null = the main sale")
    pages = serializers.ListField(child=HomeBlockPageSerializer(), required=False)
    items_count = serializers.SerializerMethodField(
        help_text="What the block shows now; for product blocks — products passing the display rules")
    items_total = serializers.SerializerMethodField(
        help_text="Product blocks only: active products of the source before the display rules")
    status = HomeBlockStatusField()

    class Meta:
        model = HomeBlock
        fields = ("id", "type", "title", "title_uz", "title_ru", "title_en", "position", "is_visible", "show_on_site",
                  "show_in_app", "banner_placement", "banner", "badge", "sale", "days", "pages", "items_count",
                  "items_total", "status", "created_at", "updated_at")
        read_only_fields = ("title", "created_at", "updated_at")
        extra_kwargs = {
            # ru is the default (fallback) language
            "title_ru": {"required": True, "allow_null": False, "allow_blank": False},
            "days": {"min_value": 1},
        }

    def _counts(self, block):
        if not hasattr(block, "_home_counts"):
            block._home_counts = home.block_counts(block, self.context["home_page"])
        return block._home_counts

    def get_items_count(self, block) -> int:
        return self._counts(block)[0]

    def get_items_total(self, block) -> Optional[int]:
        return self._counts(block)[1]

    def validate(self, attrs):
        def current(name, default=None):
            # the sent value, else the stored one (PATCH)
            if name in attrs:
                return attrs[name]
            return getattr(self.instance, name) if self.instance else default

        if self.instance:
            # the type is chosen once, when the block is added
            attrs.pop("type", None)
        if not any(current(name, True) for name in CHANNEL_FIELDS):
            raise serializers.ValidationError({"show_on_site": "Select at least one channel."})
        block_type = current("type")
        required = REQUIRED_SOURCE.get(block_type)
        if required and not current(required):
            raise serializers.ValidationError({required: f"Required for type={block_type}."})
        for name in SOURCE_FIELDS:
            if name not in TYPE_SOURCES.get(block_type, ()):
                attrs[name] = HomeBlock._meta.get_field(name).get_default()
        return attrs

    def create(self, validated_data):
        if "position" not in validated_data:
            # a new block goes to the end of the page
            validated_data["position"] = (HomeBlock.objects.aggregate(last=Max("position"))["last"] or 0) + 1
        return super().create(validated_data)


class HomeBlockReorderSerializer(CategoryReorderSerializer):
    """Drag & drop: `ids` in the new order. A tab shows only the blocks of its channel, so `ids` may be a part of
    the page — the sent blocks are rearranged within the places they take now, the others stay where they are."""

    def save(self, **kwargs):
        ids = self.validated_data["ids"]
        order = list(HomeBlock.objects.order_by("position", "id").values_list("id", flat=True))
        places = sorted(order.index(pk) for pk in ids)
        for place, pk in zip(places, ids):
            order[place] = pk
        HomeBlock.objects.bulk_update(
            [HomeBlock(id=pk, position=position) for position, pk in enumerate(order, start=1)], ["position"])


class HomePageSerializer(serializers.ModelSerializer):
    published_by = StaffShortSerializer(read_only=True, allow_null=True)
    has_changes = serializers.SerializerMethodField(
        help_text="The draft (blocks + rules) differs from the published version: enables the publish button")

    class Meta:
        model = HomePage
        fields = ("hide_out_of_stock", "hide_stale_price", "min_products", "published_at", "published_by",
                  "has_changes")
        read_only_fields = ("published_at",)

    def get_has_changes(self, page) -> bool:
        return home.has_changes(page)


class HomePagePublishSerializer(HomePageSerializer):
    """Publishes the draft: no input, returns the page."""

    class Meta(HomePageSerializer.Meta):
        read_only_fields = HomePageSerializer.Meta.fields

    def update(self, instance, validated_data):
        return home.publish(instance, self.context["request"].user)
