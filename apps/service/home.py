from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from apps.base.models import Articles, Banner, Video
from apps.service.models import AddsBrands, Brand, HomeBlock, HomePage, OrderItem, Product, ProductCategory, Sale

ORDER_CANCELED = 4

RULE_FIELDS = ("hide_out_of_stock", "hide_stale_price", "min_products")
# what "publish" stores per block; the list order is the page order
SNAPSHOT_FIELDS = ("id", "type", "title_uz", "title_ru", "title_en", "is_visible", "show_on_site", "show_in_app",
                   "banner_placement", "banner_id", "badge_id", "sale_id", "days", "pages")


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
    return page
