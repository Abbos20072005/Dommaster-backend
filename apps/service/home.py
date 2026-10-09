from datetime import timedelta
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from apps.base.models import Articles, Banner, Video
from apps.service.models import AddsBrands, Brand, HomeBlock, HomePage, OrderItem, Product, ProductBadge, \
    ProductCategory, Sale

ORDER_CANCELED = 4

RULE_FIELDS = ("hide_out_of_stock", "hide_stale_price", "min_products")
# what "publish" stores per block; the list order is the page order
SNAPSHOT_FIELDS = ("id", "type", "title_uz", "title_ru", "title_en", "is_visible", "show_on_site", "show_in_app",
                   "banner_placement", "banner_id", "badge_id", "sale_id", "days", "pages")

# client `?platform=` -> (channel flag of a block, channel flag of a banner)
PLATFORMS = {
    "site": ("show_on_site", "show_on_site"),
    "ios": ("show_in_app", "show_on_ios"),
    "android": ("show_in_app", "show_on_android"),
}
LANGUAGES = ("uz", "ru", "en")
LAYOUT_CACHE_TIMEOUT = 300


def layout_cache_key(platform, language):
    return f"home:blocks:{platform or 'all'}:{language}"


def block_sale(block):
    """Sale of a `sale_products` block: the chosen one, else the main sale."""
    return block.sale or Sale.objects.filter(is_main=True, is_visible=True).first()


def source_products(block, now=None):
    """Active products the block takes from its source, before the display rules."""
    products = Product.objects.filter(is_active=True)
    if block.type == HomeBlock.BADGE_PRODUCTS:
        return products.filter(badges=block.badge_id)
    if block.type == HomeBlock.SALE_PRODUCTS:
        sale = block_sale(block)
        return products.filter(sale_products=sale) if sale else products.none()
    if block.type == HomeBlock.NEW_PRODUCTS:
        return products.filter(created_at__gte=(now or timezone.now()) - timedelta(days=block.days))
    if block.type == HomeBlock.BESTSELLERS:
        sold = OrderItem.objects.exclude(order__status=ORDER_CANCELED).order_by()
        return products.filter(pk__in=sold.values("product"))
    return products


def apply_rules(products, page):
    """Display rules of the home page ("Ko'rsatish qoidalari")."""
    if page.hide_out_of_stock:
        products = products.filter(quantity__gt=0)
    # `hide_stale_price` has nothing to filter by: Product keeps no time of the last 1C price update
    return products


def block_counts(block, page):
    """(items the block shows now, items of its source). The second one is None for non-product blocks."""
    if block.type in HomeBlock.PRODUCT_TYPES:
        products = source_products(block)
        return apply_rules(products, page).count(), products.count()
    if block.type == HomeBlock.SLIDER:
        count = Banner.objects.filter(Banner.status_q(Banner.ACTIVE), placement=block.banner_placement).count()
    elif block.type == HomeBlock.BANNER:
        count = int(block.banner.status == Banner.ACTIVE)
    elif block.type == HomeBlock.CATEGORIES:
        count = ProductCategory.objects.filter(is_active=True).count()
    elif block.type == HomeBlock.BRANDS:
        count = Brand.objects.filter(is_visible=True, show_on_home=True).count()
    elif block.type == HomeBlock.PAGES:
        count = len(block.pages)
    elif block.type == HomeBlock.CONTENT:
        count = Articles.objects.count() + Video.objects.count()
    else:
        count = AddsBrands.objects.filter(is_visible=True).count()
    return count, None


def block_status(block, page, items_count):
    if not block.is_visible:
        return HomeBlock.HIDDEN
    if block.type in HomeBlock.PRODUCT_TYPES and items_count < page.min_products:
        return HomeBlock.RULE_HIDDEN
    return HomeBlock.VISIBLE


def draft_snapshot(page):
    """The current (draft) state of the page in the shape "publish" stores."""
    return {
        "rules": {name: getattr(page, name) for name in RULE_FIELDS},
        "blocks": list(HomeBlock.objects.order_by("position", "id").values(*SNAPSHOT_FIELDS)),
    }


def has_changes(page):
    """True when the draft differs from the published version (or nothing is published yet)."""
    return page.published_data != draft_snapshot(page)


@transaction.atomic
def publish(page, user):
    page.published_data = draft_snapshot(page)
    page.published_at = timezone.now()
    page.published_by = user
    page.save(update_fields=["published_data", "published_at", "published_by", "updated_at"])
    keys = [layout_cache_key(platform, language) for platform in (None, *PLATFORMS) for language in LANGUAGES]
    transaction.on_commit(lambda: cache.delete_many(keys))
    return page


# ---- client: the published version ----

def published_page(page):
    """(rules, blocks) of the published version as unsaved model instances; no blocks when nothing is published."""
    data = page.published_data or {}
    rules = HomePage(**{name: value for name, value in data.get("rules", {}).items() if name in RULE_FIELDS})
    blocks = [HomeBlock(**{name: row[name] for name in SNAPSHOT_FIELDS if name in row})
              for row in data.get("blocks", [])]
    return rules, blocks


def published_block(page, pk):
    """(rules, block) of a published block that is not hidden by hand, else (rules, None)."""
    rules, blocks = published_page(page)
    return rules, next((block for block in blocks if block.id == pk and block.is_visible), None)


def block_products(block, rules):
    """Products a product block shows (display rules applied), in the order of the block.
    `all_products` comes unordered: its view orders it by the random seed."""
    products = apply_rules(source_products(block), rules)
    if block.type == HomeBlock.BESTSELLERS:
        sold = Sum("product_order_item__quantity", filter=~Q(product_order_item__order__status=ORDER_CANCELED))
        return products.annotate(_sold=sold).order_by("-_sold", "-id")
    if block.type == HomeBlock.NEW_PRODUCTS:
        return products.order_by("-created_at", "-id")
    if block.type == HomeBlock.ALL_PRODUCTS:
        return products
    return products.order_by("-id")


def block_content(block, rules, platform=None):
    """What a published block shows on `platform` (None = any): a dict for the client serializer,
    or None when the block has nothing to show (other channel, source gone / inactive / empty, below the rules)."""
    block_flag, banner_flag = PLATFORMS.get(platform, (None, None))
    if not block.is_visible or (block_flag and not getattr(block, block_flag)):
        return None
    banner_channel = {banner_flag: True} if banner_flag else {}

    if block.type in HomeBlock.PRODUCT_TYPES:
        content = {}
        if block.type == HomeBlock.BADGE_PRODUCTS:
            content["badge"] = ProductBadge.objects.filter(pk=block.badge_id).first()
            if not content["badge"]:
                return None
        elif block.type == HomeBlock.SALE_PRODUCTS:
            sale = Sale.objects.filter(pk=block.sale_id).first() if block.sale_id else block_sale(block)
            if not sale or not sale.is_visible:
                return None
            block.sale = content["sale"] = sale
        count = apply_rules(source_products(block), rules).count()
        if count < max(rules.min_products, 1):
            return None
        return {**content, "products_count": count}
    if block.type == HomeBlock.SLIDER:
        banners = Banner.objects.filter(Banner.status_q(Banner.ACTIVE), placement=block.banner_placement,
                                        **banner_channel)
        return {"banners": banners} if banners else None
    if block.type == HomeBlock.BANNER:
        banner = Banner.objects.filter(Banner.status_q(Banner.ACTIVE), pk=block.banner_id, **banner_channel).first()
        return {"banner": banner} if banner else None
    if block.type == HomeBlock.CATEGORIES:
        categories = ProductCategory.objects.filter(is_active=True).order_by("position", "id")
        return {"categories": categories} if categories else None
    if block.type == HomeBlock.BRANDS:
        brands = Brand.objects.filter(is_visible=True, show_on_home=True).order_by("id")
        return {"brands": brands} if brands else None
    if block.type == HomeBlock.PAGES:
        return {"pages": block.pages} if block.pages else None
    # content, adds_brands: the client loads them from their own endpoints
    return {} if block_counts(block, rules)[0] else None
