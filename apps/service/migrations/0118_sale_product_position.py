from django.db import migrations, models
import django.db.models.deletion


def number_positions(apps, schema_editor):
    # the products of each sale keep the order they were added in
    SaleProduct = apps.get_model("service", "SaleProduct")
    rows, positions = [], {}
    for row in SaleProduct.objects.order_by("sale_id", "id"):
        positions[row.sale_id] = row.position = positions.get(row.sale_id, 0) + 1
        rows.append(row)
    SaleProduct.objects.bulk_update(rows, ["position"], batch_size=1000)


class Migration(migrations.Migration):
    # Sale.products gets an explicit through model on the table of the auto M2M (service_sale_products):
    # the table, its columns and the unique (sale, product) index stay, only `position` is added

    dependencies = [
        ('service', '0117_remove_english'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='SaleProduct',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('sale', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='product_links', to='service.sale', verbose_name='Распродажа')),
                        ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sale_links', to='service.product', verbose_name='Продукт')),
                    ],
                    options={
                        'verbose_name': 'Продукт распродажи',
                        'verbose_name_plural': 'Продукты распродажи',
                        'db_table': 'service_sale_products',
                        'ordering': ('position', 'id'),
                        'unique_together': {('sale', 'product')},
                    },
                ),
                migrations.AlterField(
                    model_name='sale',
                    name='products',
                    field=models.ManyToManyField(related_name='sale_products', through='service.SaleProduct', to='service.product', verbose_name='Продукты'),
                ),
            ],
            database_operations=[],
        ),
        migrations.AddField(
            model_name='saleproduct',
            name='position',
            field=models.PositiveIntegerField(default=0, verbose_name='Позиция'),
        ),
        migrations.RunPython(number_positions, migrations.RunPython.noop),
    ]
