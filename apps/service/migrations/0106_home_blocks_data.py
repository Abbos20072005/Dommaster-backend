from django.db import migrations

# the home page as the site / app render it today (hard-coded order), top to bottom: type, title uz, title ru, source
BLOCKS = (
    ("slider", "Asosiy slayder", "Главный слайдер", {"banner_placement": "site_home"}),
    ("categories", "Kategoriyalar", "Категории", {}),
    # sale = null: the main sale
    ("sale_products", "Chegirmadagi mahsulotlar", "Товары со скидкой", {}),
    ("brands", "Faqat original mahsulotlar", "Только оригинальные товары", {}),
    ("bestsellers", "Eng ko'p sotilgan mahsulotlar", "Самые продаваемые товары", {}),
    ("content", "Maqola / Videolar", "Статьи / Видео", {}),
    ("adds_brands", "Asosiy bo'limlar", "Основные разделы", {}),
    ("all_products", "Barcha mahsulotlar", "Все товары", {}),
)


def forwards(apps, schema_editor):
    HomeBlock = apps.get_model("service", "HomeBlock")
    if HomeBlock.objects.exists():
        return
    HomeBlock.objects.bulk_create([
        HomeBlock(type=block_type, title=title_ru, title_uz=title_uz, title_ru=title_ru, position=position, **source)
        for position, (block_type, title_uz, title_ru, source) in enumerate(BLOCKS, start=1)
    ])


class Migration(migrations.Migration):

    dependencies = [
        ('service', '0105_home_blocks'),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
