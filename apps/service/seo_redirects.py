"""Old-slug -> current-slug resolution for 301 redirects (SlugHistory).

A slug is per language. When SeoFieldsMixin.save() sees a `slug_<lang>` change, it calls `record_change`
to keep the old value. The client `seo/resolve/` endpoint calls `resolve` so the site can 301 an old or
renamed URL to the product / brand / category's current slug.

Products keep no history: their slug ends with `-<id>` and follows a rename, so an old product slug is
resolved by that id.
"""
import re

from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from .models import (Brand, Product, ProductCategory, ProductItemCategory, ProductSubCategory, SlugHistory)

DEFAULT_LANGUAGE = "ru"
# the `-<id>` end of a SLUG_WITH_ID slug (Product)
TRAILING_ID = re.compile(r"-(\d+)$")

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


def resolve(entity_type, slug, language):
    """Return {status, type, id, slug} for a slug, or None when nothing matches.

    status: `current` (slug is live), `moved` (slug is an old one -> `slug` is the current one; a product's
    old slug is found by the id at its end).
    """
    model = ENTITY_TYPES.get(entity_type)
    if not model or not slug:
        return None
    if language not in settings.MODELTRANSLATION_LANGUAGES:
        language = DEFAULT_LANGUAGE
    field = f"slug_{language}"

    obj = _visible_queryset(model).filter(**{field: slug}).first()
    if obj:
        return {"status": "current", "type": entity_type, "id": obj.pk, "slug": slug}

    content_type = ContentType.objects.get_for_model(model)
    row = SlugHistory.objects.filter(content_type=content_type, language=language, old_slug=slug).first()
    if row:
        obj = _visible_queryset(model).filter(pk=row.object_id).first()
        if obj:
            current = getattr(obj, field, None) or getattr(obj, "slug_ru", None)
            return {"status": "moved", "type": entity_type, "id": obj.pk, "slug": current}

    match = TRAILING_ID.search(slug) if model.SLUG_WITH_ID else None
    if match:
        obj = _visible_queryset(model).filter(pk=int(match.group(1))).first()
        current = obj and (getattr(obj, field, None) or getattr(obj, "slug_ru", None))
        if current:
            return {"status": "moved", "type": entity_type, "id": obj.pk, "slug": current}
    return None
