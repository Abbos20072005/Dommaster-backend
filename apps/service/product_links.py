"""Hand-made product links for the client: related products and alternatives on the product page, cross-sell for the
cart (`RelatedProduct` / `AlternativeProduct` / `CrossSellProduct`). Only what can be bought now is shown: active, with
a price, a picture and stock (`feed.eligible_products`)."""
from apps.service import feed
from apps.service.models import AlternativeProduct, CrossSellProduct, ProductVariantItem, RelatedProduct

LIMIT = 10

# where the alternatives come from: picked in the admin panel, or (none of them can be shown) the item category
ALTERNATIVES_MANUAL = "manual"
ALTERNATIVES_CATEGORY = "category"


def _ordered(ids):
    """Eligible products of `ids` in that order, at most LIMIT."""
    found = set(feed.eligible_products().filter(pk__in=ids).values_list("pk", flat=True))
    return [pk for pk in ids if pk in found][:LIMIT]


def _linked_ids(model, product):
    return list(model.products_of(product).values_list("pk", flat=True))


def related_ids(product):
    return _ordered(_linked_ids(RelatedProduct, product))


def alternative_ids(product):
    """(ids, source): the alternatives picked by hand; none of them can be shown -> the popular products of the
    product's item category (other variants of the product are left out: the product card lists them already)."""
    ids = _ordered(_linked_ids(AlternativeProduct, product))
    if ids:
        return ids, ALTERNATIVES_MANUAL
    if not product.product_item_category_id:
        return [], None

    variants = ProductVariantItem.objects.filter(group__items__product=product).values_list("product_id", flat=True)
    candidates = feed.eligible_products().filter(product_item_category_id=product.product_item_category_id) \
        .exclude(pk=product.pk).exclude(pk__in=variants).values_list("pk", flat=True)
    popularity = feed.product_popularity()
    ids = sorted(candidates, key=lambda pk: (-popularity.get(pk, 0), pk))[:LIMIT]
    return ids, ALTERNATIVES_CATEGORY if ids else None


def cart_cross_sell_ids(cart_product_ids):
    """Cross-sell of the products in the cart (`cart_product_ids`, newest first): the first link of every product,
    then the second ones and so on; products already in the cart are left out."""
    order = {pk: index for index, pk in enumerate(cart_product_ids)}
    links = CrossSellProduct.objects.filter(product_id__in=order).exclude(linked_product_id__in=order) \
        .values_list("product_id", "linked_product_id", "position")
    ids = [linked for _, linked, _ in sorted(links, key=lambda link: (link[2], order[link[0]]))]
    return _ordered(list(dict.fromkeys(ids)))
