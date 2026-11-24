"""Fills `Banner.desktop_image_ru` / `mobile_image_ru` from the banner's old single image columns.

Run once after migrate base 0033 (`manage.py backfill_banner_images`): registering the images for translation
added the empty `*_uz` / `*_ru` columns, and modeltranslation reads only those - until they are filled, every
banner looks like it has no image. The ru columns point to the same files (nothing is copied on disk); the uz
ones stay empty on purpose: an empty uz image falls back to ru, and the content team uploads the real uz ones.

Safe to run again: only the ru columns that are still empty are touched.
"""
from django.core.management.base import BaseCommand
from django.db.models import F, Q

from apps.base.models import Banner

FIELDS = ("desktop_image", "mobile_image")


class Command(BaseCommand):
    help = "Copies the old Banner.desktop_image / mobile_image into the *_ru columns (run once after migrate 0033)"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Only report what would change")

    def handle(self, *args, **options):
        for name in FIELDS:
            ru = f"{name}_ru"
            # rewrite(False): without it modeltranslation turns `desktop_image` into `desktop_image_ru` in the
            # query itself, and the old column - the one we are reading from - stays invisible to the ORM
            pending = Banner.objects.rewrite(False).filter(Q(**{f"{ru}__isnull": True}) | Q(**{ru: ""})) \
                .exclude(Q(**{f"{name}__isnull": True}) | Q(**{name: ""}))
            if options["dry_run"]:
                ids = list(pending.values_list("id", flat=True))
                self.stdout.write(f"Would fill {ru} of {len(ids)} banner(s): {ids[:50]}")
                continue
            filled = pending.update(**{ru: F(name)})
            self.stdout.write(self.style.SUCCESS(f"{ru} filled for {filled} banner(s)"))
