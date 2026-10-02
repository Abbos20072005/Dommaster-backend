from django.db import migrations, models

from utils.slug import slugify_latin

CATEGORY_MODELS = ("ProductCategory", "ProductSubCategory", "ProductItemCategory")


def fill_slugs(apps, schema_editor):
    for model_name in CATEGORY_MODELS:
        model = apps.get_model("service", model_name)
        used = set()
        for obj in model.objects.order_by("id").only("id", "name", "name_uz", "name_ru"):
            base = slugify_latin(obj.name_uz or obj.name_ru or obj.name)[:247].strip("-") or "category"
            slug, n = base, 1
            while slug in used:
                n += 1
                slug = f"{base}-{n}"
            used.add(slug)
            model.objects.filter(pk=obj.pk).update(slug=slug)


class Migration(migrations.Migration):

    dependencies = [
        ('service', '0096_category_slug_seo_visibility'),
    ]

    operations = [
        migrations.RunPython(fill_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='productcategory',
            name='slug',
            field=models.SlugField(blank=True, max_length=255, unique=True, verbose_name='Slug'),
        ),
        migrations.AlterField(
            model_name='productitemcategory',
            name='slug',
            field=models.SlugField(blank=True, max_length=255, unique=True, verbose_name='Slug'),
        ),
        migrations.AlterField(
            model_name='productsubcategory',
            name='slug',
            field=models.SlugField(blank=True, max_length=255, unique=True, verbose_name='Slug'),
        ),
    ]
