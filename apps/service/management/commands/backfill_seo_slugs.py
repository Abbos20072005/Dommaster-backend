"""Fill the per-language SEO slugs (slug_uz / slug_ru) after migration 0121.

Schema-only migrations add the columns empty; this command populates them (CLAUDE.md: data changes go into
a management command, not a migration). Safe to re-run — it only fills empty slugs.

Categories already had one ASCII `slug` (the original column): it is kept as `slug_ru`; `slug_uz` and the
product / brand slugs are generated from the name via `utils.slug.unique_slug_for`.

    manage.py backfill_seo_slugs [--dry-run]
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.service.models import (Brand, Product, ProductCategory, ProductItemCategory, ProductSubCategory)
from utils.slug import unique_slug_for

CATEGORY_MODELS = (ProductCategory, ProductSubCategory, ProductItemCategory)
MODELS = (Product, Brand) + CATEGORY_MODELS


class Command(BaseCommand):
    help = "Fill slug_uz / slug_ru for products, brands and categories (run once after migrate)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report what would change, save nothing.")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        languages = settings.MODELTRANSLATION_LANGUAGES

        for model in MODELS:
            # raw original `slug` column (modeltranslation shadows obj.slug with slug_ru, which is still empty)
            legacy = {}
            if model in CATEGORY_MODELS:
                legacy = dict(model.objects.values_list("pk", "slug"))

            filled = 0
            for obj in model.objects.all().iterator():
                changed = False
                for language in languages:
                    field = f"slug_{language}"
                    if getattr(obj, field, None):
                        continue
                    # ru of a category: keep its existing single slug when there is one
                    source_slug = legacy.get(obj.pk) if (language == "ru" and model in CATEGORY_MODELS) else None
                    if source_slug and not model.objects.exclude(pk=obj.pk).filter(**{field: source_slug}).exists():
                        value = source_slug
                    else:
                        value = unique_slug_for(model, obj._slug_source(language), field=field, exclude_pk=obj.pk,
                                                fallback=obj.SLUG_FALLBACK)
                    setattr(obj, field, value)
                    changed = True
                if changed:
                    filled += 1
                    if not dry_run:
                        obj.save()
            verb = "would fill" if dry_run else "filled"
            self.stdout.write(f"{model.__name__}: {verb} {filled} row(s)")

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — nothing saved."))
        else:
            self.stdout.write(self.style.SUCCESS("Done."))
