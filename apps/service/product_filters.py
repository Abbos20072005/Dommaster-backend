"""Client product filters, built from the attributes of the item categories and the products' attribute values.

A filter key is the attribute id as a string ("37"); "price" is the only built-in one.
"""
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, Exists, Max, Min, OuterRef

from .attributes import display_value, translated
from .models import Product, ProductAttribute, ProductAttributeValue, ProductItemCategoryAttribute

PRICE_KEY = "price"
RANGE, CHECKBOX = "range", "checkbox"
PRICE_LABELS = {"uz": ("Narx", "so'm"), "ru": ("Цена", "сум"), "en": ("Price", "UZS")}
CACHE_TTL = 86400


def cache_key(item_category_id, language):
    return f"product:available_filters:cat:{item_category_id}:{language}"


def clear_category_filter_cache(*item_category_ids):
    """Drop the cached filters of the item categories, once the current transaction is committed."""
    keys = [cache_key(pk, language) for pk in item_category_ids if pk
            for language in settings.MODELTRANSLATION_LANGUAGES]
    if keys:
        transaction.on_commit(lambda: cache.delete_many(keys))


def _number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _attribute_id(key):
    return int(key) if key.isdigit() and len(key) < 10 else None


def _range_lookups(field, value):
    bounds = {"gte": _number(value.get("min")), "lte": _number(value.get("max"))}
    return {f"{field}__{lookup}": bound for lookup, bound in bounds.items() if bound is not None}


def apply_attribute_filters(products, filters):
    """`filters` of the request: {"price": {"min", "max"}, "<attribute id>": [values] or {"min", "max"}}.

    Values are the `value` of the available filters (the ru text of the attribute value).
    Unknown keys and attributes that are not filterable are ignored.
    """
    if not isinstance(filters, dict):
        return products

    attributes = ProductAttribute.objects.filter(
        id__in=[pk for pk in map(_attribute_id, filters) if pk], is_filterable=True, is_active=True,
    ).in_bulk()

    for key, value in filters.items():
        if key == PRICE_KEY:
            if isinstance(value, dict):
                products = products.filter(**_range_lookups("price", value))
            continue

        attribute = attributes.get(_attribute_id(key))
        if attribute is None:
            continue

        values = ProductAttributeValue.objects.filter(product=OuterRef("pk"), attribute=attribute)
        if isinstance(value, dict):
            lookups = _range_lookups("value_number", value)
            if not lookups:
                continue
            values = values.filter(**lookups)
        else:
            values = values.filter(value_ru__in=[str(item) for item in (value if isinstance(value, list) else [value])])
        products = products.filter(Exists(values))
    return products


def build_available_filters(products, item_category_ids, language):
    """Filters of the item categories' attributes, with the values / ranges `products` have.

    Returns (filters, quick_filters): `number` attributes are ranges, the rest are checkboxes with value counts.
    """
    links = ProductItemCategoryAttribute.objects.filter(
        item_category_id__in=item_category_ids, attribute__is_filterable=True, attribute__is_active=True,
    ).select_related("attribute").order_by("position", "id")
    by_attribute = {}
    for link in links:
        # several categories (search results): the first category's settings win
        by_attribute.setdefault(link.attribute_id, link)

    number_ids = [pk for pk, link in by_attribute.items() if link.attribute.value_type == ProductAttribute.NUMBER]
    rows = ProductAttributeValue.objects.filter(attribute_id__in=list(by_attribute), product__in=products)

    ranges = {
        row["attribute_id"]: row
        for row in rows.filter(attribute_id__in=number_ids, value_number__isnull=False)
        .values("attribute_id").annotate(min=Min("value_number"), max=Max("value_number"))
    }

    # one grouped query for every checkbox filter
    values = {}
    counts = rows.exclude(attribute_id__in=number_ids).exclude(value_ru__isnull=True).exclude(value_ru="") \
        .values(*{"attribute_id", "value_ru", f"value_{language}"}).annotate(count=Count("id"))
    for row in counts:
        value = row["value_ru"]
        value_type = by_attribute[row["attribute_id"]].attribute.value_type
        item = values.setdefault(row["attribute_id"], {}).setdefault(value, {
            "value": value,
            "label": display_value(value_type, row[f"value_{language}"] or value, language),
            "count": 0,
        })
        item["count"] += row["count"]

    filters, quick_filters = [], []
    price = products.aggregate(min=Min("price"), max=Max("price"))
    if price["min"] is not None:
        label, unit = PRICE_LABELS[language]
        filters.append({"key": PRICE_KEY, "label": label, "type": RANGE, "unit": unit,
                        "min": price["min"], "max": price["max"]})

    for attribute_id, link in by_attribute.items():
        attribute = link.attribute
        key, label = str(attribute_id), translated(attribute, "name", language)
        if attribute_id in ranges:
            filters.append({"key": key, "label": label, "type": RANGE, "unit": attribute.unit,
                            "min": ranges[attribute_id]["min"], "max": ranges[attribute_id]["max"]})
        elif attribute_id in values:
            items = sorted(values[attribute_id].values(), key=lambda item: (-item["count"], item["value"]))
            filters.append({"key": key, "label": label, "type": CHECKBOX, "unit": "", "values": items})
            if link.is_quick_filter:
                for item in items[:link.max_quick_filters or None]:
                    quick_filters.append({"key": key, "label": item["label"], "value": item["value"],
                                          "count": item["count"]})
    return filters, quick_filters


def category_filters(item_category_id, language):
    """Filters of an item category over all its active products (cached)."""
    key = cache_key(item_category_id, language)
    cached = cache.get(key)
    if cached is None:
        products = Product.objects.filter(product_item_category_id=item_category_id, is_active=True)
        filters, quick_filters = build_available_filters(products, [item_category_id], language)
        cached = {"filters": filters, "quick": quick_filters}
        cache.set(key, cached, timeout=CACHE_TTL)
    return cached["filters"], cached["quick"]
