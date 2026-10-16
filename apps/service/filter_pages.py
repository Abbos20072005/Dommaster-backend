"""SEO landing pages of filter combinations (FilterPage): item category + optional brand + attribute filters.

`filters` has the shape of `product/filter` `filters` ({"<attribute id>": [ru values] or {"min", "max"},
"price": {"min", "max"}}), so the client loads a page's products with `POST product/filter/` and the body
`product_filter_body(page)`. A page is open (client detail, sitemap list) while `open_pages()` has it.
"""
import hashlib
import json

from django.db.models import Q
from django.utils import timezone

from .attributes import translated
from .models import FilterPage, Product, ProductAttribute, ProductItemCategoryAttribute
from .product_filters import PRICE_KEY, apply_attribute_filters


class FilterPageError(ValueError):
    pass


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_range(value):
    if not isinstance(value, dict):
        return None
    bounds = {key: _number(value.get(key)) for key in ("min", "max")}
    return {key: bound for key, bound in bounds.items() if bound is not None} or None


def _normalize_values(value):
    values = value if isinstance(value, list) else [value]
    return sorted({str(item).strip() for item in values if item is not None and str(item).strip()}) or None


def normalize_filters(filters):
    """Canonical form: ranges as floats, value lists sorted and unique, empty filters dropped."""
    normalized = {}
    for key, value in (filters or {}).items():
        key = str(key)
        value = _normalize_range(value) if isinstance(value, dict) else _normalize_values(value)
        if value:
            normalized[key] = value
    return normalized


def combination_hash(item_category_id, brand_id, filters):
    key = json.dumps([item_category_id, brand_id, normalize_filters(filters)], sort_keys=True, ensure_ascii=False)
    return hashlib.md5(key.encode()).hexdigest()


def clean_filters(item_category_id, filters):
    """Normalized `filters` of a page; raises FilterPageError when a filter is not one the item category's
    clients can pick (filterable active attribute of the category, existing option, valid range)."""
    if not isinstance(filters, dict):
        raise FilterPageError("filters must be an object.")
    attributes = {
        str(link.attribute_id): link.attribute
        for link in ProductItemCategoryAttribute.objects.filter(
            item_category_id=item_category_id, attribute__is_filterable=True, attribute__is_active=True,
        ).select_related("attribute")
    }
    cleaned = {}
    for key, value in filters.items():
        key = str(key)
        attribute = attributes.get(key)
        if key != PRICE_KEY and attribute is None:
            raise FilterPageError(f"{key}: not a filter of the item category.")

        if key == PRICE_KEY or attribute.value_type == ProductAttribute.NUMBER:
            bounds = _normalize_range(value)
            if not bounds:
                raise FilterPageError(f"{key}: a range {{\"min\", \"max\"}} with at least one number is required.")
            if bounds.get("min", float("-inf")) > bounds.get("max", float("inf")):
                raise FilterPageError(f"{key}: min is greater than max.")
            cleaned[key] = bounds
            continue

        values = _normalize_values(value) if not isinstance(value, dict) else None
        if not values:
            raise FilterPageError(f"{key}: a list of values is required.")
        if attribute.value_type == ProductAttribute.LIST:
            allowed = set(attribute.options.values_list("value_ru", flat=True))
        elif attribute.value_type == ProductAttribute.BOOLEAN:
            allowed = {"true", "false"}
        else:
            allowed = None
        unknown = [item for item in values if allowed is not None and item not in allowed]
        if unknown:
            raise FilterPageError(f"{key}: unknown values {', '.join(unknown)}.")
        cleaned[key] = values
    return cleaned


def page_products(page):
    products = Product.objects.filter(is_active=True, product_item_category_id=page.item_category_id)
    if page.brand_id:
        products = products.filter(brand_id=page.brand_id)
    return apply_attribute_filters(products, page.filters)


def refresh_counts(pages=None):
    """Recount the products of the pages (all of them by default); returns how many counts changed."""
    changed, now = 0, timezone.now()
    for page in pages if pages is not None else FilterPage.objects.all():
        count = page_products(page).count()
        changed += count != page.products_count
        page.products_count, page.counted_at = count, now
        FilterPage.objects.filter(pk=page.pk).update(products_count=count, counted_at=now)
    return changed


def open_pages():
    """Pages clients and search engines get: active, enough products, category and brand shown."""
    return FilterPage.objects.filter(
        Q(brand__isnull=True) | Q(brand__is_visible=True),
        is_active=True, products_count__gte=FilterPage.MIN_PRODUCTS, item_category__is_active=True,
    )


def find_page(item_category_id, brand_id, filters):
    """Open page of exactly this filter combination, or None."""
    return open_pages().filter(combination_hash=combination_hash(item_category_id, brand_id, filters)).first()


def product_filter_body(page):
    body = {"item_category": page.item_category_id, "filters": page.filters}
    if page.brand_id:
        body["brand"] = page.brand_id
    return body


META_DESCRIPTION_LENGTH = 160


def _short(text, length=META_DESCRIPTION_LENGTH):
    text = " ".join((text or "").split())
    if len(text) <= length:
        return text
    return text[:length].rsplit(" ", 1)[0].rstrip(",.;:-") + "…"


def page_list_data(page, language):
    """Sitemap / category page link; reads page.item_category."""
    return {
        "slug": page.slug,
        "title": translated(page, "title", language),
        "item_category": {"id": page.item_category_id, "slug": page.item_category.slug},
        "brand": page.brand_id,
        "products_count": page.products_count,
        "updated_at": page.updated_at,
    }


def page_detail_data(page, language):
    """Client page: texts in `language` (empty uz -> ru), breadcrumbs, body for `product/filter/`;
    reads page.item_category up to the category and page.brand."""
    title, text = translated(page, "title", language), translated(page, "text", language) or ""
    item_category = page.item_category
    levels = (
        ("product_category", item_category.product_sub_category.product_category),
        ("product_sub_category", item_category.product_sub_category),
        ("product_item_category", item_category),
    )
    return {
        "id": page.id,
        "slug": page.slug,
        "title": title,
        "meta_title": translated(page, "meta_title", language) or title,
        "meta_description": translated(page, "meta_description", language) or _short(text),
        "text": text,
        "item_category": {"id": item_category.id, "name": translated(item_category, "name", language),
                          "slug": item_category.slug},
        "brand": {"id": page.brand.id, "name": translated(page.brand, "name", language)} if page.brand else None,
        "breadcrumbs": [{"id": obj.id, "name": translated(obj, "name", language), "slug": obj.slug, "level": level}
                        for level, obj in levels],
        "product_filter": product_filter_body(page),
        "products_count": page.products_count,
        "updated_at": page.updated_at,
    }
