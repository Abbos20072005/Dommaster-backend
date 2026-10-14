"""Moderation queue of products: a product sent for publishing (`publish_status=review`) waits in the queue as a
pending `ProductModeration` row until an admin approves (-> published) or rejects (-> draft, with a reason) it.
Approving needs every readiness check done (`readiness`)."""
from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone
from django.utils.html import strip_tags

from apps.service.models import Product, ProductItemCategoryAttribute, ProductModeration
from apps.service.models.choices import PUBLISH_STATUS_DRAFT, PUBLISH_STATUS_PUBLISHED, PUBLISH_STATUS_REVIEW

# readiness checks, in the order of the admin panel's checklist; every one is required for approving
NAME_UZ = "name_uz"
NAME_RU = "name_ru"
DESCRIPTION_UZ = "description_uz"
DESCRIPTION_RU = "description_ru"
IMAGE = "image"
REQUIRED_ATTRIBUTES = "required_attributes"
CATEGORY = "category"
BRAND = "brand"
CHECKS = (NAME_UZ, NAME_RU, DESCRIPTION_UZ, DESCRIPTION_RU, IMAGE, REQUIRED_ATTRIBUTES, CATEGORY, BRAND)

# why a row could not be reviewed
NOT_PENDING = "not_pending"
NOT_READY = "not_ready"


class ModerationError(Exception):
    def __init__(self, reason, missing=()):
        super().__init__(reason)
        self.reason = reason
        self.missing = list(missing)


def readiness_prefetch(prefix=""):
    """Lookups `readiness` reads, for `prefetch_related` (prefix = path to the product, e.g. "product__")."""
    return [
        f"{prefix}product_image",
        f"{prefix}attribute_values",
        Prefetch(f"{prefix}product_item_category__attribute_links",
                 queryset=ProductItemCategoryAttribute.objects.filter(is_required=True, attribute__is_active=True)
                 .select_related("attribute"),
                 to_attr="required_links"),
    ]


def readiness_queryset():
    return Product.objects.select_related("brand", "product_item_category").prefetch_related(*readiness_prefetch())


def has_text(html):
    return bool(strip_tags(html or "").replace("&nbsp;", " ").strip())


def readiness(product):
    """What the product lacks for publishing. Reads the prefetched relations of `readiness_prefetch`."""
    category = product.product_item_category
    missing_attributes = []
    if category:
        links = getattr(category, "required_links", None)
        if links is None:
            links = category.attribute_links.filter(is_required=True, attribute__is_active=True) \
                .select_related("attribute")
        filled = {value.attribute_id for value in product.attribute_values.all()}
        missing_attributes = [link.attribute for link in links if link.attribute_id not in filled]
    done = {
        NAME_UZ: bool((product.name_uz or "").strip()),
        NAME_RU: bool((product.name_ru or "").strip()),
        DESCRIPTION_UZ: has_text(product.description_uz),
        DESCRIPTION_RU: has_text(product.description_ru),
        IMAGE: bool(product.product_image.all()),
        REQUIRED_ATTRIBUTES: not missing_attributes,
        CATEGORY: category is not None,
        BRAND: product.brand_id is not None,
    }
    missing = [key for key in CHECKS if not done[key]]
    return {
        "done": len(CHECKS) - len(missing),
        "total": len(CHECKS),
        "ready": not missing,
        "missing": missing,
        "checks": [{"key": key, "done": done[key]} for key in CHECKS],
        "missing_attributes": missing_attributes,
    }


def _set_publish_status(product, publish_status):
    if product.publish_status != publish_status:
        product.publish_status = publish_status
        product.save(update_fields=["publish_status", "updated_at"])


def on_publish_status_change(product, old_status, user):
    """`publish_status` changed in the product form: keeps the queue in step with it.
    review -> a pending row; published by hand -> the pending row is approved (no readiness check);
    back to draft -> the pending row is dropped (the submission is taken back)."""
    new_status = product.publish_status
    if new_status == old_status:
        return
    pending = ProductModeration.objects.filter(product=product, status=ProductModeration.PENDING)
    if new_status == PUBLISH_STATUS_REVIEW:
        if not pending.exists():
            ProductModeration.objects.create(product=product, submitted_by=user)
    elif new_status == PUBLISH_STATUS_PUBLISHED:
        pending.update(status=ProductModeration.APPROVED, reviewed_by=user, reviewed_at=timezone.now())
    else:
        pending.delete()


def _lock_pending(moderation_id):
    row = ProductModeration.objects.select_for_update().filter(pk=moderation_id).first()
    if row is None or row.status != ProductModeration.PENDING:
        raise ModerationError(NOT_PENDING)
    return row


@transaction.atomic
def approve(moderation_id, user):
    """Approves a pending row and publishes its product. Raises `ModerationError` (nothing changes) when the row is
    not pending or the product fails a readiness check."""
    row = _lock_pending(moderation_id)
    product = readiness_queryset().get(pk=row.product_id)
    missing = readiness(product)["missing"]
    if missing:
        raise ModerationError(NOT_READY, missing)
    row.status = ProductModeration.APPROVED
    row.reviewed_by = user
    row.reviewed_at = timezone.now()
    row.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
    _set_publish_status(product, PUBLISH_STATUS_PUBLISHED)
    return row


@transaction.atomic
def reject(moderation_id, user, reason):
    """Returns a pending row's product to draft with the reason."""
    row = _lock_pending(moderation_id)
    row.status = ProductModeration.REJECTED
    row.reviewed_by = user
    row.reviewed_at = timezone.now()
    row.reason = reason
    row.save(update_fields=["status", "reviewed_by", "reviewed_at", "reason", "updated_at"])
    _set_publish_status(row.product, PUBLISH_STATUS_DRAFT)
    return row
