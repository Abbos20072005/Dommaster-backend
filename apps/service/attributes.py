"""Product attribute values as customers see them (product cards, filters)."""
from django.conf import settings
from django.db.models import OuterRef, Prefetch, Subquery
from django.utils.translation.trans_real import parse_accept_lang_header

from .models import ProductAttribute, ProductAttributeValue, ProductItemCategoryAttribute

DEFAULT_LANGUAGE = "ru"
BOOLEAN_LABELS = {
    "uz": {"true": "Ha", "false": "Yo'q"},
    "ru": {"true": "Да", "false": "Нет"},
}
# Product attribute the prefetched values are stored in (see attribute_values_prefetch)
VALUES_ATTR = "_attribute_values"


def request_language(request):
    """The first of our languages in Accept-Language ("uz", "uz-UZ", "uz-UZ,uz;q=0.9,ru;q=0.8"), else ru."""
    header = request.META.get("HTTP_ACCEPT_LANGUAGE", "") if request else ""
    for language, _ in parse_accept_lang_header(header):
        language = language.split("-")[0]
        if language in settings.MODELTRANSLATION_LANGUAGES:
            return language
    return DEFAULT_LANGUAGE


def translated(obj, field, language):
    # ru is the default (fallback) language
    return getattr(obj, f"{field}_{language}", None) or getattr(obj, f"{field}_{DEFAULT_LANGUAGE}")


def display_value(value_type, value, language):
    """Stored value -> what the customer reads (booleans are kept as "true" / "false")."""
    if value_type == ProductAttribute.BOOLEAN:
        return BOOLEAN_LABELS[language].get(value, value)
    return value


def attribute_values_queryset():
    """Values of the active attributes, in the order the attributes have in the product's item category."""
    position = ProductItemCategoryAttribute.objects.filter(
        attribute=OuterRef("attribute_id"), item_category=OuterRef("product__product_item_category_id"),
    ).values("position")[:1]
    return ProductAttributeValue.objects.filter(attribute__is_active=True).select_related("attribute") \
        .annotate(position=Subquery(position)).order_by("position", "id")


def attribute_values_prefetch():
    return Prefetch("attribute_values", queryset=attribute_values_queryset(), to_attr=VALUES_ATTR)


def product_attribute_values(product):
    """The product's values to show; one query unless the product came with attribute_values_prefetch()."""
    values = getattr(product, VALUES_ATTR, None)
    if values is None:
        values = list(attribute_values_queryset().filter(product=product))
        setattr(product, VALUES_ATTR, values)
    return values
