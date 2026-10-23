"""Old-slug -> current-slug resolution for 301 redirects (SlugHistory).

A slug is per language. When SeoFieldsMixin.save() sees a `slug_<lang>` change, it calls `record_change`
to keep the old value. The client `seo/resolve/` endpoint calls `resolve` so the site can 301 an old or
renamed URL to the product / brand / category's current slug.

Products keep no history: their slug ends with `-<id>` and follows a rename, so an old product slug is
resolved by that id. A hidden or deleted product is `gone`: the site 301s it to `redirect` (a hand-picked
alternative, else the nearest active category) or answers 410 when there is none. Deleted products / news are
remembered in DeletedObject (`record_deletion`, called by a pre_delete signal).
"""
import re

from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from .models import (AlternativeProduct, Brand, DeletedObject, Product, ProductCategory, ProductItemCategory,
                     ProductSubCategory, SlugHistory)
from .utils import build_breadcrumbs

DEFAULT_LANGUAGE = "ru"
# the `-<id>` end of a SLUG_WITH_ID slug (Product); a bare id is accepted too (`/product/<id>` links)
TRAILING_ID = re.compile(r"(?:^|-)(\d+)$")

# entity type (what the front puts in the URL) -> model
ENTITY_TYPES = {
    "product": Product,
    "category": ProductCategory,
    "sub_category": ProductSubCategory,
    "item_category": ProductItemCategory,
    "brand": Brand,
}


def _visible_queryset(model):
    """Only objects a client page would actually serve."""
    if model is Brand:
        return model.objects.filter(is_visible=True)
    return model.objects.filter(is_active=True)


def record_change(obj, language, old_slug):
    """Remember that `obj` used `old_slug` in `language`. Latest object using a freed slug wins."""
    if not old_slug:
        return
    content_type = ContentType.objects.get_for_model(type(obj))
    SlugHistory.objects.update_or_create(
        content_type=content_type, language=language, old_slug=old_slug,
        defaults={"object_id": obj.pk},
    )


def record_deletion(obj, item_category_id=None, alternative_ids=()):
    """Remember a deleted product / news row (inside the delete's transaction)."""
    DeletedObject.objects.update_or_create(
        content_type=ContentType.objects.get_for_model(type(obj)), object_id=obj.pk,
        defaults={"item_category_id": item_category_id, "alternative_ids": list(alternative_ids)},
    )


def deleted_row(model, pk):
    return DeletedObject.objects.filter(content_type=ContentType.objects.get_for_model(model), object_id=pk).first()


def _target(obj, entity_type, language):
    return {"type": entity_type, "id": obj.pk, "slug": translated_slug(obj, language),
            "breadcrumbs": build_breadcrumbs(obj, language)}


def translated_slug(obj, language):
    return getattr(obj, f"slug_{language}", None) or getattr(obj, "slug_ru", None)


BREADCRUMB_RELATED = "product_item_category__product_sub_category__product_category"


def gone_redirect(alternative, item_category_id, language):
    """Where a gone product's URL goes: its active alternative, else the nearest active category level."""
    if alternative is not None:
        return _target(alternative, "product", language)
    item = (ProductItemCategory.objects.select_related("product_sub_category__product_category")
            .filter(pk=item_category_id).first() if item_category_id else None)
    sub = item and item.product_sub_category
    for level, entity_type in ((item, "item_category"), (sub, "sub_category"),
                               (sub and sub.product_category, "category")):
        if level is not None and level.is_active:
            return _target(level, entity_type, language)
    return None


def _gone_product(slug, field, language):
    match = TRAILING_ID.search(slug)
    product = Product.objects.filter(**{field: slug}).first()
    if product is None and match:
        product = Product.objects.filter(pk=int(match.group(1))).first()
    if product is not None:
        # still in the database, so hidden (an active one is answered before this)
        alternative = (AlternativeProduct.products_of(product).filter(is_active=True)
                       .select_related(BREADCRUMB_RELATED).first())
        redirect = gone_redirect(alternative, product.product_item_category_id, language)
        return {"status": "gone", "type": "product", "id": product.pk, "slug": None, "redirect": redirect}
    row = match and deleted_row(Product, int(match.group(1)))
    if row:
        active = {p.pk: p for p in Product.objects.filter(pk__in=row.alternative_ids, is_active=True)
                  .select_related(BREADCRUMB_RELATED)}
        alternative = next((active[pk] for pk in row.alternative_ids if pk in active), None)
        redirect = gone_redirect(alternative, row.item_category_id, language)
        return {"status": "gone", "type": "product", "id": row.object_id, "slug": None, "redirect": redirect}
    return None


def resolve(entity_type, slug, language):
    """Return {status, type, id, slug, redirect} for a slug, or None when nothing matches.

    status: `current` (slug is live), `moved` (slug is an old one -> `slug` is the current one; a product's
    old slug is found by the id at its end), `gone` (product hidden or deleted -> 301 to `redirect`, or 410
    when it is null).
    """
    model = ENTITY_TYPES.get(entity_type)
    if not model or not slug:
        return None
    if language not in settings.MODELTRANSLATION_LANGUAGES:
        language = DEFAULT_LANGUAGE
    field = f"slug_{language}"

    obj = _visible_queryset(model).filter(**{field: slug}).first()
    if obj:
        return {"status": "current", "type": entity_type, "id": obj.pk, "slug": slug, "redirect": None}

    content_type = ContentType.objects.get_for_model(model)
    row = SlugHistory.objects.filter(content_type=content_type, language=language, old_slug=slug).first()
    if row:
        obj = _visible_queryset(model).filter(pk=row.object_id).first()
        if obj:
            current = translated_slug(obj, language)
            return {"status": "moved", "type": entity_type, "id": obj.pk, "slug": current, "redirect": None}

    match = TRAILING_ID.search(slug) if model.SLUG_WITH_ID else None
    if match:
        obj = _visible_queryset(model).filter(pk=int(match.group(1))).first()
        current = obj and translated_slug(obj, language)
        if current:
            return {"status": "moved", "type": entity_type, "id": obj.pk, "slug": current, "redirect": None}
    if model is Product:
        return _gone_product(slug, field, language)
    return None
