import re
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from service.models import (
    Product, ProductCharacteristics, ProductItemCategoryFilterSchema,
    ProductFilterNumericValue,
)


def parse_numeric(raw_value):
    if not raw_value:
        return None
    cleaned = re.sub(r'[^\d.,]', '', str(raw_value)).replace(',', '.')
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def detect_type_for_value(raw_value, unit):
    if unit and unit.lower() in ("kg", "g", "l", "m", "sm", "cm", "mm", "kw", "w", "v", "a"):
        return "range"
    return "range" if parse_numeric(raw_value) is not None else "checkbox"


class Command(BaseCommand):
    help = "Backfill filter_data and ProductFilterNumericValue from existing ProductCharacteristics"

    def handle(self, *args, **options):
        products = Product.objects.prefetch_related("product_characteristics").iterator(chunk_size=500)
        total = 0

        for product in products:
            filter_data = {}
            chars = list(product.product_characteristics.all())

            for char in chars:
                if not char.name or not char.value:
                    continue

                key = slugify(char.name, allow_unicode=True) or slugify(char.name, allow_unicode=False)

                schema, _ = ProductItemCategoryFilterSchema.objects.get_or_create(
                    item_category=product.product_item_category,
                    key=key,
                    defaults={
                        "source_name_ru": char.name,
                        "label": char.name,
                        "unit": char.unit or "",
                    }
                )

                if schema.type_locked:
                    detected = schema.type
                else:
                    detected = detect_type_for_value(char.value, char.unit)

                if detected != schema.type and not schema.type_locked:
                    schema.type = detected
                    schema.save(update_fields=["type"])

                if schema.type == "range":
                    numeric_val = parse_numeric(char.value)
                    if numeric_val is not None:
                        ProductFilterNumericValue.objects.update_or_create(
                            product=product, schema=schema,
                            defaults={"value": numeric_val}
                        )
                else:
                    filter_data[key] = slugify(char.value, allow_unicode=True) or char.value

            product.filter_data = filter_data
            Product.objects.filter(id=product.id).update(filter_data=filter_data)
            total += 1

            if total % 100 == 0:
                self.stdout.write(f"Backfilled {total} products...")

        self.stdout.write(self.style.SUCCESS(f"Successfully backfilled {total} products"))
