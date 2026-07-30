from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("service", "0075_order_products_total_price"),
    ]

    operations = [
        migrations.RenameField(
            model_name="product",
            old_name="vendor_code",
            new_name="articul_code",
        ),
        migrations.RemoveField(
            model_name="product",
            name="guid",
        ),
        migrations.AddField(
            model_name="product",
            name="product_code",
            field=models.CharField(blank=True, max_length=100, null=True, unique=True, verbose_name="Код из 1С"),
        ),
    ]
