import openpyxl
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.service.models import Product

from .apply_audit_corrections import clean

# A sheet of products that are on the site already: our product id + a supplier price in dollars
# ("Saytda bor (narx)": ID / Saytdagi nomi / ... / Narx (USD)). price = round(USD × (1 + markup %) × rate).
ID_COLUMNS = ("id", "ea id")
NAME_COLUMNS = ("saytdagi nomi",)
PRICE_COLUMNS = ("narx (usd)",)


class Command(BaseCommand):
    help = (
        "Set Product.price from a sheet of product ids and dollar prices: round(USD × (1 + markup/100) × rate). "
        "Only the price is touched. Run with --dry-run first."
    )

    def add_arguments(self, parser):
        parser.add_argument("file", help="Path to the workbook (.xlsx).")
        parser.add_argument("--sheet", help="Sheet to read (default: the first one).")
        parser.add_argument("--usd-rate", type=float, required=True, help="So'm per dollar.")
        parser.add_argument("--markup", type=float, default=0, help="Percent added to the dollar price.")
        parser.add_argument("--dry-run", action="store_true", help="Roll everything back at the end.")

    def handle(self, *args, **options):
        rows = self.read_rows(options["file"], options["sheet"])
        factor = (1 + options["markup"] / 100) * options["usd_rate"]
        self.stdout.write(f"Rows: {len(rows)}, price = round(USD × {factor:g})")
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("DRY RUN - everything below is rolled back at the end"))

        changed = same = 0
        missing, renamed, discounted, one_c = [], [], [], []
        with transaction.atomic():
            products = Product.objects.select_for_update().in_bulk([pk for pk, _, _ in rows])
            for pk, name, usd in rows:
                product = products.get(pk)
                if not product:
                    missing.append(pk)
                    continue
                if name and clean(name).lower() != clean(product.name_ru).lower():
                    renamed.append((pk, name, product.name_ru))
                price = float(round(usd * factor))
                if product.discount_price:
                    discounted.append((pk, product.discount_price))
                if product.product_code:
                    one_c.append(pk)
                if product.price == price:
                    same += 1
                    continue
                self.stdout.write(f"  {pk} {product.name_ru!r}: {product.price:.0f} -> {price:.0f}")
                product.price = price
                product.save(update_fields=["price", "updated_at"])
                changed += 1
            if options["dry_run"]:
                transaction.set_rollback(True)

        self.stdout.write("")
        self.stdout.write(f"  prices changed: {changed}")
        self.stdout.write(f"  already this price: {same}")
        if missing:
            self.warn(f"no product with id: {' '.join(map(str, missing))}")
        for pk, name, current in renamed:
            self.warn(f"{pk}: the sheet says {name!r}, the product is {current!r} - check the id")
        if discounted:
            self.warn("discount_price set (the cart charges it, not the new price): "
                      + ", ".join(f"{pk} ({price:.0f})" for pk, price in discounted))
        if one_c:
            self.warn(f"{len(one_c)} products have a 1C code: 1C sets the price again when it re-sends the card")
        self.stdout.write(self.style.SUCCESS("DRY RUN finished, nothing saved" if options["dry_run"] else "Done"))

    def warn(self, message):
        self.stdout.write(self.style.WARNING(f"  ! {message}"))

    @staticmethod
    def read_rows(path, sheet=None):
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
        if sheet and sheet not in workbook.sheetnames:
            raise CommandError(f"No sheet {sheet!r}, the workbook has {workbook.sheetnames}")
        rows = (workbook[sheet] if sheet else workbook.worksheets[0]).iter_rows(values_only=True)
        for row in rows:
            headers = [clean(value).lower() for value in row]
            columns = [next((headers.index(name) for name in names if name in headers), None)
                       for names in (ID_COLUMNS, NAME_COLUMNS, PRICE_COLUMNS)]
            if columns[0] is not None and columns[2] is not None:
                break
        else:
            raise CommandError(f"No header row with the columns {ID_COLUMNS} and {PRICE_COLUMNS}")

        result = []
        for number, row in enumerate(rows, 2):
            pk, name, usd = (row[index] if index is not None and index < len(row) else None for index in columns)
            if pk in (None, ""):
                continue
            try:
                result.append((int(pk), clean(name), float(str(usd).replace(",", "."))))
            except (TypeError, ValueError):
                raise CommandError(f"Row {number}: id {pk!r} / price {usd!r} is not a number")
        workbook.close()
        return result
