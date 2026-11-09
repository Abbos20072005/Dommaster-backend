"""The functions the assistant model may call. Each returns a small JSON-able dict (tokens cost money).

Prices and stock reach the model only from here; every product id a tool returns is remembered in
`ToolContext.seen_ids` — only those may become product cards of the answer.
"""
import html
import logging
from dataclasses import dataclass, field

from django.db.models import Count
from django.utils.html import strip_tags

from apps.service import feed, product_links
from apps.service.attributes import attribute_values_prefetch, display_value, product_attribute_values, translated
from apps.service.models import Product, ProductItemCategory
from apps.service.product_filters import apply_attribute_filters, category_filters
from apps.service.search import search_products as text_search

logger = logging.getLogger(__name__)

MAX_RESULTS = 10        # products of one search_products call
DEFAULT_RESULTS = 8
MAX_QUERIES = 3         # query variants of one search (uz, ru, brand)
CANDIDATES = 50         # best matches taken from each query variant before merging
ROW_ATTRIBUTES = 5      # characteristics in a list row (the details tool returns all of them)
DESCRIPTION_CHARS = 500
FILTER_VALUES = 15      # checkbox values of one filter returned to the model


@dataclass
class ToolContext:
    language: str
    seen_ids: set = field(default_factory=set)


def _price(product):
    """(price the cart charges, crossed-out price or None) — the merchant feed rule."""
    if product.discount_price and product.discount_price > 0:
        old = product.price if product.price and product.price > product.discount_price else None
        return product.discount_price, old
    return product.price, None


def _attributes(product, language, limit=None):
    rows = []
    for value in product_attribute_values(product)[:limit]:
        attribute = value.attribute
        text = display_value(attribute.value_type, translated(value, "value", language), language)
        if not text:
            continue
        rows.append({"name": translated(attribute, "name", language), "value": text,
                     **({"unit": attribute.unit} if attribute.unit else {})})
    return rows


def _row(product, language):
    price, old_price = _price(product)
    row = {
        "id": product.pk,
        "name": product.name,
        "brand": product.brand.name if product.brand_id else None,
        "category": product.product_item_category.name if product.product_item_category_id else None,
        "price": price,
        "in_stock": product.quantity > 0,
        "unit": product.unit,
        "attributes": _attributes(product, language, ROW_ATTRIBUTES),
    }
    if old_price:
        row["old_price"] = old_price
    if product.rating:
        row["rating"] = product.rating
    return row


def _products(ids, ctx):
    """Rows of the products `ids`, in that order; their ids become the cards the answer may show."""
    qs = Product.objects.filter(pk__in=ids, is_active=True).select_related(
        "brand", "product_item_category").prefetch_related(attribute_values_prefetch())
    by_id = {product.pk: product for product in qs}
    rows = [_row(by_id[pk], ctx.language) for pk in ids if pk in by_id]
    ctx.seen_ids.update(row["id"] for row in rows)
    return rows


def _number(value):
    try:
        return float(value) if value is not None and value != "" else None
    except (TypeError, ValueError):
        return None


def _filters(items):
    """The model's list of filters -> the `filters` dict of `product/filter` (apply_attribute_filters)."""
    filters = {}
    for item in items or []:
        if not isinstance(item, dict) or not str(item.get("attribute_id", "")).strip():
            continue
        key = str(item["attribute_id"]).strip()
        values = [str(value) for value in item.get("values") or [] if str(value).strip()]
        if values:
            filters[key] = values
        elif _number(item.get("min")) is not None or _number(item.get("max")) is not None:
            filters[key] = {"min": _number(item.get("min")), "max": _number(item.get("max"))}
    return filters


def search_products(ctx, queries=None, item_category_id=None, price_min=None, price_max=None, filters=None,
                    in_stock_only=False, limit=DEFAULT_RESULTS):
    limit = max(1, min(int(limit or DEFAULT_RESULTS), MAX_RESULTS))
    products = Product.objects.filter(is_active=True)
    if item_category_id:
        products = products.filter(product_item_category_id=item_category_id)
    if _number(price_min) is not None:
        products = products.filter(price__gte=_number(price_min))
    if _number(price_max) is not None:
        products = products.filter(price__lte=_number(price_max))
    if in_stock_only:
        products = products.filter(quantity__gt=0)
    products = apply_attribute_filters(products, _filters(filters))

    queries = [str(query).strip()[:100] for query in (queries or []) if str(query).strip()][:MAX_QUERIES]
    if queries:
        scores = {}
        for query in queries:
            for pk, similarity in text_search(products, query).order_by("-similarity", "id") \
                    .values_list("id", "similarity")[:CANDIDATES]:
                scores[pk] = max(scores.get(pk, 0), similarity or 0)
        found = sorted(scores, key=lambda pk: (-scores[pk], pk))
    elif item_category_id:
        # no words, only a category (+ filters): its popular products first
        popularity = feed.product_popularity()
        found = sorted(products.values_list("id", flat=True), key=lambda pk: (-popularity.get(pk, 0), pk))
    else:
        return {"total": 0, "products": [], "categories": [], "note": "send queries or item_category_id"}

    return {"total": len(found), "products": _products(found[:limit], ctx), "categories": _categories(found)}


def _categories(ids):
    """The item categories the found products are in, most products first (top 5)."""
    rows = (Product.objects.filter(pk__in=ids, product_item_category__isnull=False)
            .values("product_item_category").annotate(count=Count("id")).order_by("-count")[:5])
    counts = {row["product_item_category"]: row["count"] for row in rows}
    names = dict(ProductItemCategory.objects.filter(pk__in=counts).values_list("pk", "name"))
    return [{"id": pk, "name": names.get(pk), "count": count} for pk, count in counts.items()]


def get_category_filters(ctx, item_category_id):
    filters, _ = category_filters(item_category_id, ctx.language)
    rows = []
    for item in filters:
        row = {"attribute_id": item["key"], "name": item["label"], "type": item["type"]}
        if item.get("unit"):
            row["unit"] = item["unit"]
        if item["type"] == "range":
            row.update(min=item.get("min"), max=item.get("max"))
        else:
            # `value` goes back in search_products filters; `label` is what the customer reads
            row["values"] = [
                {"value": value["value"], "count": value["count"],
                 **({"label": value["label"]} if value["label"] != value["value"] else {})}
                for value in sorted(item.get("values", []), key=lambda value: -value["count"])[:FILTER_VALUES]
            ]
        rows.append(row)
    return {"item_category_id": item_category_id, "filters": rows}


def get_product_details(ctx, product_id):
    product = Product.objects.filter(pk=product_id, is_active=True).select_related(
        "brand", "product_item_category").first()
    if product is None:
        return {"error": "product not found"}
    row = _row(product, ctx.language)
    row["attributes"] = _attributes(product, ctx.language)
    row["comments_quantity"] = product.comments_quantity
    for name in ("short_description", "description"):
        text = html.unescape(strip_tags(getattr(product, name) or "")).strip()
        if text:
            row[name] = " ".join(text.split())[:DESCRIPTION_CHARS]
    ctx.seen_ids.add(product.pk)
    return row


def get_alternatives(ctx, product_id):
    product = Product.objects.filter(pk=product_id).first()
    if product is None:
        return {"error": "product not found"}
    alternatives, _ = product_links.alternative_ids(product)
    return {
        "alternatives": _products(alternatives[:5], ctx),
        "bought_together": _products(product_links.related_ids(product)[:5], ctx),
    }


TOOLS = {
    "search_products": search_products,
    "get_category_filters": get_category_filters,
    "get_product_details": get_product_details,
    "get_alternatives": get_alternatives,
}


def run(name, args, ctx):
    """Call the tool `name`; a bad call is answered with an error the model can read, never raised."""
    function = TOOLS.get(name)
    if function is None:
        return {"error": f"unknown tool {name}"}
    try:
        return function(ctx, **dict(args or {}))
    except TypeError as error:
        return {"error": f"bad arguments: {error}"}
    except Exception:
        logger.exception("assistant tool %s failed", name)
        return {"error": "tool failed"}


def result_count(result):
    """How many things a tool returned (for the message log)."""
    if "products" in result:
        return len(result["products"])
    if "filters" in result:
        return len(result["filters"])
    if "alternatives" in result:
        return len(result["alternatives"]) + len(result["bought_together"])
    return 0 if "error" in result else 1


# function declarations for Gemini (JSON schema)
FILTERS_SCHEMA = {
    "type": "array",
    "description": "Attribute filters from get_category_filters: values for a checkbox filter, min / max for a range",
    "items": {
        "type": "object",
        "properties": {
            "attribute_id": {"type": "string"},
            "values": {"type": "array", "items": {"type": "string"}},
            "min": {"type": "number"},
            "max": {"type": "number"},
        },
        "required": ["attribute_id"],
    },
}

DECLARATIONS = [
    {
        "name": "search_products",
        "description": (
            "Search the Buildex catalog (building materials, tools, plumbing, electrics). Send 1-3 short keyword "
            "variants of what the customer wants: Uzbek Latin, Russian and the brand / model if named, e.g. "
            "[\"perforator\", \"перфоратор\", \"Bosch GBH\"]. Returns products (price in UZS, in_stock, top "
            "attributes) and the item categories they are in."
        ),
        "parameters_json_schema": {
            "type": "object",
            "properties": {
                "queries": {"type": "array", "items": {"type": "string"}, "maxItems": MAX_QUERIES},
                "item_category_id": {"type": "integer", "description": "Only products of this item category"},
                "price_min": {"type": "number"},
                "price_max": {"type": "number"},
                "filters": FILTERS_SCHEMA,
                "in_stock_only": {"type": "boolean"},
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS},
            },
        },
    },
    {
        "name": "get_category_filters",
        "description": "The attributes a customer can filter an item category by, with their possible values.",
        "parameters_json_schema": {
            "type": "object",
            "properties": {"item_category_id": {"type": "integer"}},
            "required": ["item_category_id"],
        },
    },
    {
        "name": "get_product_details",
        "description": "All attributes, description, price and stock of one product.",
        "parameters_json_schema": {
            "type": "object",
            "properties": {"product_id": {"type": "integer"}},
            "required": ["product_id"],
        },
    },
    {
        "name": "get_alternatives",
        "description": "Products that can replace a product, and products bought together with it.",
        "parameters_json_schema": {
            "type": "object",
            "properties": {"product_id": {"type": "integer"}},
            "required": ["product_id"],
        },
    },
]
