"""Fills `MarketBranch.address_ru` from the branch's old single `address` column.

Run once after migrate 0031 (`manage.py backfill_branch_address`): registering `address` for translation
added the empty `address_uz` / `address_ru` columns, and modeltranslation reads only those - until they are
filled, every branch looks like it has no address. `address_uz` is left empty on purpose: an empty uz text
falls back to ru, and the content team can see which branches still need a real uz translation.

Safe to run again: only branches whose `address_ru` is still empty are touched.
"""
from django.core.management.base import BaseCommand
from django.db.models import F, Q

from apps.base.models import MarketBranch


class Command(BaseCommand):
    help = "Copies the old MarketBranch.address into address_ru (run once after migrate 0031)"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Only report what would change")

    def _printable(self, text):
        """A Windows console is usually cp125x: a Cyrillic name must not kill the command."""
        encoding = getattr(self.stdout, "encoding", None) or "utf-8"
        return str(text).encode(encoding, "replace").decode(encoding, "replace")

    def handle(self, *args, **options):
        # rewrite(False): without it modeltranslation turns `address` into `address_ru` in the query itself,
        # and the old column - the one we are reading from - stays invisible to the ORM
        pending = MarketBranch.objects.rewrite(False).filter(
            Q(address_ru__isnull=True) | Q(address_ru=""),
        ).exclude(Q(address__isnull=True) | Q(address=""))

        if options["dry_run"]:
            rows = list(pending.values_list("id", "name", "address")[:20])
            self.stdout.write(f"Would fill address_ru of {pending.count()} branch(es)")
            for branch_id, name, address in rows:
                self.stdout.write(self._printable(f"  #{branch_id} {name}: {address}"))
            return

        filled = pending.update(address_ru=F("address"))
        self.stdout.write(self.style.SUCCESS(f"address_ru filled for {filled} branch(es)"))
