"""Empty string -> NULL in the translation columns where an empty string blocks the fallback.

modeltranslation falls back to ru only when the value it finds is the field's "undefined" value - the
field default. For a `null=True` column (MarketBranch.address, Product.short_description, ...) that is
NULL, so an empty string counts as a filled value and a uz client sees nothing instead of the ru text.
1C, the old admin forms and DRF all write "" rather than NULL, so the rows have to be normalized once.

Run after `migrate`; safe to run again (it only touches rows that are still ""):

    manage.py backfill_empty_translations [--dry-run]
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from modeltranslation.translator import translator
from modeltranslation.utils import build_localized_fieldname

from django.conf import settings


def columns_to_fix():
    """(model, column) pairs where "" is not the field's undefined value, so it would block the fallback."""
    for model in translator.get_registered_models():
        options = translator.get_options_for_model(model)
        for field_name in sorted(options.fields):
            field = model._meta.get_field(field_name)
            if field.get_default() == "":
                continue  # "" already means "not filled" here, modeltranslation falls back by itself
            for language in settings.MODELTRANSLATION_LANGUAGES:
                yield model, build_localized_fieldname(field_name, language)


class Command(BaseCommand):
    help = 'Replaces "" with NULL in the translation columns where "" would block the ru fallback'

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="only count the rows, change nothing")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        total = 0
        with transaction.atomic():
            for model, column in columns_to_fix():
                rows = model.objects.filter(**{column: ""})
                count = rows.count()
                if not count:
                    continue
                total += count
                label = f"{model._meta.label}.{column}"
                if dry_run:
                    self.stdout.write(f"  {label}: {count} row(s) would become NULL")
                else:
                    rows.update(**{column: None})
                    self.stdout.write(f"  {label}: {count} row(s) -> NULL")
            if dry_run:
                transaction.set_rollback(True)

        if not total:
            self.stdout.write(self.style.SUCCESS("Nothing to do - no empty strings in those columns"))
        elif dry_run:
            self.stdout.write(self.style.WARNING(f"DRY RUN: {total} row(s) would change"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Done: {total} row(s) changed"))
