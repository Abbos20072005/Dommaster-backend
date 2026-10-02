from django.db import migrations

# value types removed from VALUE_TYPE_CHOICES -> the closest remaining one
VALUE_TYPE_MAP = {"range": "number", "multi_list": "list", "color": "list"}


def forwards(apps, schema_editor):
    ProductAttribute = apps.get_model("service", "ProductAttribute")
    ProductItemCategoryAttribute = apps.get_model("service", "ProductItemCategoryAttribute")

    # item_category FK (removed in 0092) -> item_categories M2M
    ProductItemCategoryAttribute.objects.bulk_create(
        [
            ProductItemCategoryAttribute(item_category_id=item_category_id, attribute_id=attribute_id)
            for attribute_id, item_category_id in ProductAttribute.objects.values_list("id", "item_category_id")
        ],
        ignore_conflicts=True,
    )
    for old, new in VALUE_TYPE_MAP.items():
        ProductAttribute.objects.filter(value_type=old).update(value_type=new)


class Migration(migrations.Migration):

    dependencies = [
        ('service', '0090_attribute_dictionary'),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
