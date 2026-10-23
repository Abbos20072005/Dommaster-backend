"""Fill — or rebuild — the per-language SEO slugs (slug_uz / slug_ru) of products, brands and categories.

Schema-only migrations add the columns empty; this command populates them (CLAUDE.md: data changes go into
a management command, not a migration).

    manage.py backfill_seo_slugs [--dry-run]            # fill the empty columns only (safe to re-run)
    manage.py backfill_seo_slugs --rebuild [--dry-run]   # regenerate every slug by the current table
    manage.py backfill_seo_slugs --products [--dry-run]  # product slugs that no longer match the name

`--rebuild` is what a change of the transliteration table (`utils/slug.CYRILLIC_TO_LATIN`) needs: it throws
away the slugs that are in the db — including the ones entered by hand, which is the 22.10 decision — and
generates them from the name again. The old slug of a category / brand goes to `SlugHistory`, so
`seo/resolve/` answers `moved` and the site 301s the old URL (products keep no history, their slug carries
the id). The rebuild also clears the original `slug` column (the pre-SEO single slug, from the old table):
nothing reads it, the per-language columns are the slugs.

`--products` touches products only: every `slug_<lang>` that differs from what the current name gives is
generated again. A product slug used to stay as it was when the name changed (the audit renames left
"…-asfora-antratsit-571" for "… Asfora 10 А, антрацит"); since then a rename moves it (`SLUG_FOLLOWS_NAME`),
this is the one-off fix of the slugs made before that. A hand-made product slug can't be told apart and is
regenerated too. No history — the id at the end stays the same, so the site still finds the product.
"""
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.service.models import (Brand, Product, ProductCategory, ProductItemCategory, ProductSubCategory)
from apps.service.seo_redirects import record_change
from utils.slug import slug_base, slug_with_id

CATEGORY_MODELS = (ProductCategory, ProductSubCategory, ProductItemCategory)
MODELS = (Product, Brand) + CATEGORY_MODELS
BATCH = 500


class Command(BaseCommand):
    help = "Fill slug_uz / slug_ru for products, brands and categories (--rebuild regenerates all of them)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report what would change, save nothing.")
        parser.add_argument("--rebuild", action="store_true",
                            help="Regenerate every slug from the name by the current transliteration table.")
        parser.add_argument("--products", action="store_true",
                            help="Regenerate only the product slugs that no longer match the product name.")

    def handle(self, *args, **options):
        self.dry_run = options["dry_run"]
        if options["products"]:
            self._refresh_products()
            self._done()
            return
        for model in MODELS:
            if options["rebuild"]:
                self._rebuild(model)
            else:
                self._fill(model)
        self._done()

    def _done(self):
        if self.dry_run:
            self.stdout.write(self.style.WARNING("Dry run — nothing saved."))
        else:
            self.stdout.write(self.style.SUCCESS("Done."))

    def _slug_fields(self):
        return [f"slug_{language}" for language in settings.MODELTRANSLATION_LANGUAGES]

    def _raw(self, model):
        """Queryset without modeltranslation's field rewriting, so `slug` means the original column."""
        queryset = model._default_manager.all()
        return queryset.rewrite(False) if hasattr(queryset, "rewrite") else queryset

    # fill: only the empty columns, the slugs that are there stay as they are
    def _fill(self, model):
        filled = 0
        for obj in model.objects.all().iterator(chunk_size=BATCH):
            fields = obj.fill_slugs()
            if not fields:
                continue
            filled += 1
            if not self.dry_run:
                self._raw(model).filter(pk=obj.pk).update(**{field: getattr(obj, field) for field in fields})
        verb = "would fill" if self.dry_run else "filled"
        self.stdout.write(f"{model.__name__}: {verb} {filled} row(s)")

    # products: only the slugs that the current name would not give
    def _refresh_products(self):
        languages = settings.MODELTRANSLATION_LANGUAGES
        slug_fields = self._slug_fields()
        changed = {field: 0 for field in slug_fields}
        refreshed, batch = 0, []
        with transaction.atomic():
            for product in Product.objects.order_by("pk").iterator(chunk_size=BATCH):
                stale = False
                for language in languages:
                    field = f"slug_{language}"
                    value = product._generated_slug(language)
                    if getattr(product, field) != value:
                        setattr(product, field, value)
                        changed[field] += 1
                        stale = True
                if stale:
                    refreshed += 1
                    batch.append(product)
                    if len(batch) >= BATCH:
                        self._write(Product, batch, slug_fields)
                        batch = []
            self._write(Product, batch, slug_fields)
        verb = "would refresh" if self.dry_run else "refreshed"
        per_field = ", ".join(f"{field} {count}" for field, count in changed.items())
        self.stdout.write(f"Product: {verb} {refreshed} row(s) ({per_field})")

    # rebuild: every slug from the name again (a changed transliteration table)
    def _rebuild(self, model):
        languages = settings.MODELTRANSLATION_LANGUAGES
        slug_fields = self._slug_fields()
        # the old slugs are needed for the 301 history (categories / brands); products keep none
        previous = {}
        if model.SLUG_HISTORY:
            previous = {row["pk"]: row for row in model.objects.values("pk", *slug_fields)}

        with transaction.atomic():
            if not self.dry_run:
                # free every slug first: a row may take the slug another row still holds
                self._raw(model).update(**{field: None for field in slug_fields + ["slug"]})

            taken = {field: set() for field in slug_fields}
            rebuilt, moved, batch = 0, [], []
            for obj in model.objects.order_by("pk").iterator(chunk_size=BATCH):
                old = previous.get(obj.pk, {})
                for language in languages:
                    field = f"slug_{language}"
                    value = self._new_slug(model, obj, language, field, taken[field])
                    setattr(obj, field, value)
                    if old.get(field) and old[field] != value:
                        moved.append((obj, language, old[field]))
                rebuilt += 1
                batch.append(obj)
                if len(batch) >= BATCH:
                    self._write(model, batch, slug_fields)
                    batch = []
            self._write(model, batch, slug_fields)

            if not self.dry_run:
                for obj, language, old_slug in moved:
                    record_change(obj, language, old_slug)

        verb = "would rebuild" if self.dry_run else "rebuilt"
        history = f", {len(moved)} old slug(s) kept for 301" if model.SLUG_HISTORY else ""
        self.stdout.write(f"{model.__name__}: {verb} {rebuilt} row(s){history}")

    def _new_slug(self, model, obj, language, field, taken):
        source = obj._slug_source(language)
        if model.SLUG_WITH_ID:
            return slug_with_id(model, source, obj.pk, field=field, fallback=model.SLUG_FALLBACK)
        # the whole table is rewritten, so the new values are deduped here instead of a query per row
        base = slug_base(model, source, field=field, fallback=model.SLUG_FALLBACK)
        value, n = base, 1
        while value in taken:
            n += 1
            value = f"{base}-{n}"
        taken.add(value)
        return value

    def _write(self, model, batch, slug_fields):
        if batch and not self.dry_run:
            model.objects.bulk_update(batch, slug_fields, batch_size=BATCH)
