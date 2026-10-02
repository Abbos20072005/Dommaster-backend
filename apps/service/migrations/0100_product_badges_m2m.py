from django.db import migrations, models


def copy_badges(apps, schema_editor):
    Product = apps.get_model("service", "Product")
    link = Product.badges.through
    link.objects.bulk_create(
        [link(product_id=product_id, productbadge_id=badge_id)
         for product_id, badge_id in Product.objects.filter(badge__isnull=False).values_list("pk", "badge_id")],
        batch_size=1000,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('service', '0099_product_badge_rules'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='productbadge',
            options={'ordering': ('position', 'id'), 'verbose_name': 'Бейдж продукта', 'verbose_name_plural': 'Бейджи продуктов'},
        ),
        migrations.AddField(
            model_name='product',
            name='badges',
            field=models.ManyToManyField(blank=True, related_name='products', to='service.productbadge', verbose_name='Бейджи'),
        ),
        # Product.badge (FK) -> Product.badges (M2M)
        migrations.RunPython(copy_badges, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='product',
            name='badge',
        ),
    ]
