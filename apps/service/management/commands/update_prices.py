import re

import openpyxl
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.service.models import Brand, Product
from utils.price import round_price_up

from .apply_audit_corrections import clean

# 1) A sheet of products that are on the site already: our product id + a supplier price in dollars
#    ("Saytda bor (narx)": ID / Saytdagi nomi / ... / Narx (USD)). price = USD × (1 + markup %) × rate, rounded up to 100 so'm.
# 2) A supplier price list without our ids (NOVA: Наименование / Цена с НДС, the price in so'm): the product is
#    found by the articul at the end of the name ("..., 4802.uz" → articul_code 4802), else by the exact name.
#    price = price × (1 + markup %) [× rate when --usd-rate is given], rounded up to 100 so'm.
ID_COLUMNS = ("id", "ea id")
NAME_COLUMNS = ("saytdagi nomi",)
PRICE_COLUMNS = ("narx (usd)",)
LIST_NAME_COLUMNS = ("наименование",)
LIST_PRICE_COLUMNS = ("цена с ндс", "цена", "цена, uzs", "цена (uzs)", "цена (1 штуку)")
# "Выпускной механизм Nova универсальный 4802.uz", "Гофра ..., 7044.tr", "Трап ..., 5650.002.uz"
TRAILING_CODE = re.compile(r"[\s,:]+(\d{3,6}(?:\.\d{1,3})?)\.[a-z]{2}$", re.IGNORECASE)
BIG_CHANGE = 0.5  # a new price more than 50% away from the old one is listed for a second look


def words(text):
    return set(re.findall(r"[0-9a-zа-яё]{2,}", clean(text).lower().replace("ё", "е")))


class Command(BaseCommand):
    help = (
        "Set Product.price from a sheet: product ids + dollar prices (round(USD × (1 + markup/100) × rate)), "
        "or a supplier price list without ids (Наименование + Цена с НДС in so'm, product by the articul at the "
        "end of the name, else by the name). Only the price is touched. Run with --dry-run first."
    )

    def add_arguments(self, parser):
        parser.add_argument("file", help="Path to the workbook (.xlsx).")
        parser.add_argument("--sheet", help="Sheet to read (default: the first one).")
        parser.add_argument("--usd-rate", type=float,
                            help="So'm per dollar. Required for the id sheet; a price list is in so'm without it.")
        parser.add_argument("--markup", type=float, default=0, help="Percent added to the sheet price.")
        parser.add_argument("--brand", help="Price list: look for the products of this brand only.")
        parser.add_argument("--dry-run", action="store_true", help="Roll everything back at the end.")

    def handle(self, *args, **options):
        mode, rows = self.read_rows(options["file"], options["sheet"])
        if mode == "id" and not options["usd_rate"]:
            raise CommandError("--usd-rate is required for a sheet of product ids and dollar prices")
        factor = (1 + options["markup"] / 100) * (options["usd_rate"] or 1)
        unit = "USD" if options["usd_rate"] else "so'm"
        self.stdout.write(f"Rows: {len(rows)}, price = round({unit} × {factor:g})")
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("DRY RUN - everything below is rolled back at the end"))

        changed = same = 0
        missing, renamed, discounted, one_c, big, hidden = [], [], [], [], [], []
        with transaction.atomic():
            if mode == "id":
                products = Product.objects.select_for_update().in_bulk([pk for pk, _, _ in rows])
                matched = [(products.get(pk), name, value, pk) for pk, name, value in rows]
            else:
                matched = self.match_by_name(rows, options["brand"])
            for product, name, value, row in matched:
                if not product:
                    missing.append(row)
                    continue
                if mode == "id" and name and clean(name).lower() != clean(product.name_ru).lower():
                    renamed.append((product.pk, name, product.name_ru))
                exact = value * factor
                price = round_price_up(exact)
                if product.discount_price:
                    discounted.append((product.pk, product.discount_price))
                if product.product_code:
                    one_c.append(product.pk)
                # prices are stored rounded up to 100 so'm (Product.save): 35503.95 -> 35600
                if product.price == price:
                    same += 1
                    continue
                self.stdout.write(f"  {product.pk} {product.name_ru!r}: {product.price or 0:.0f} -> {price:.0f}"
                                  + ("" if product.is_active else "  (hidden)"))
                if product.price and abs(price - product.price) / product.price > BIG_CHANGE:
                    big.append((product.pk, product.price, price))
                if not product.is_active:
                    hidden.append(product.pk)
                product.price = price
                product.save(update_fields=["price", "updated_at"])
                changed += 1
            if options["dry_run"]:
                transaction.set_rollback(True)

        self.stdout.write("")
        self.stdout.write(f"  prices changed: {changed}" + (f" ({len(hidden)} of them hidden products)" if hidden else ""))
        self.stdout.write(f"  already this price: {same}")
        if missing:
            if mode == "id":
                self.warn(f"no product with id: {' '.join(map(str, missing))}")
            else:
                for row in missing:
                    self.warn(f"not found / not sure, skipped: {row}")
        for pk, name, current in renamed:
            self.warn(f"{pk}: the sheet says {name!r}, the product is {current!r} - check the id")
        for pk, old, new in big:
            self.warn(f"{pk}: {old:.0f} -> {new:.0f} is a change of more than {BIG_CHANGE:.0%} - check the row")
        if discounted:
            self.warn("discount_price set (the cart charges it, not the new price): "
                      + ", ".join(f"{pk} ({price:.0f})" for pk, price in discounted))
        if one_c:
            self.warn(f"{len(one_c)} products have a 1C code: 1C sets the price again when it re-sends the card")
        self.stdout.write(self.style.SUCCESS("DRY RUN finished, nothing saved" if options["dry_run"] else "Done"))

    def match_by_name(self, rows, brand_name):
        """[(product or None, name, price, row label)] - a product taken by two rows is skipped in both."""
        products = Product.objects.select_for_update()
        if brand_name:
            brand = Brand.objects.filter(name__iexact=brand_name).first()
            if not brand:
                raise CommandError(f"No brand {brand_name!r}")
            products = products.filter(brand=brand)
        result = []
        for number, name, value in rows:
            label = f"row {number} {name!r}"
            code = TRAILING_CODE.search(name)
            if code:
                code = code.group(1)
                candidates = list(products.filter(articul_code__iexact=code)) or list(
                    products.filter(name_ru__iregex=rf"(^|[^0-9.]){re.escape(code)}([^0-9.]|$)"))
            else:
                candidates = list(products.filter(name_ru__iexact=name))
            if len(candidates) > 1:
                # one articul for several products (the sheet's slip: KARE / NEW BUBBLE / VERTICAL LINE) →
                # the one whose name shares the most words with the row
                sheet_words = words(name)
                scored = sorted(((len(sheet_words & words(p.name_ru)), p) for p in candidates),
                                key=lambda item: -item[0])
                candidates = [scored[0][1]] if scored[0][0] > scored[1][0] else []
            result.append((candidates[0] if candidates else None, name, value, label))
        taken = {}
        for product, *_ in result:
            if product:
                taken[product.pk] = taken.get(product.pk, 0) + 1
        return [(None, name, value, f"{label} - the same product {product.pk} as another row")
                if product and taken[product.pk] > 1 else (product, name, value, label)
                for product, name, value, label in result]

    def warn(self, message):
        self.stdout.write(self.style.WARNING(f"  ! {message}"))

    @staticmethod
    def read_rows(path, sheet=None):
        """("id", [(id, name, price)]) or ("list", [(row number, name, price)])."""
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
        if sheet and sheet not in workbook.sheetnames:
            raise CommandError(f"No sheet {sheet!r}, the workbook has {workbook.sheetnames}")
        rows = enumerate((workbook[sheet] if sheet else workbook.worksheets[0]).iter_rows(values_only=True), 1)
        for _, row in rows:
            headers = [clean(value).lower() for value in row]
            find = lambda names: next((headers.index(name) for name in names if name in headers), None)  # noqa: E731
            if find(ID_COLUMNS) is not None and find(PRICE_COLUMNS) is not None:
                mode, columns = "id", [find(ID_COLUMNS), find(NAME_COLUMNS), find(PRICE_COLUMNS)]
                break
            if find(LIST_NAME_COLUMNS) is not None and find(LIST_PRICE_COLUMNS) is not None:
                mode, columns = "list", [None, find(LIST_NAME_COLUMNS), find(LIST_PRICE_COLUMNS)]
                break
        else:
            raise CommandError(f"No header row with the columns {ID_COLUMNS} + {PRICE_COLUMNS} "
                               f"or {LIST_NAME_COLUMNS} + {LIST_PRICE_COLUMNS}")

        result = []
        for number, row in rows:
            pk, name, price = (row[index] if index is not None and index < len(row) else None for index in columns)
            if mode == "list":
                # section titles ("Арматура для бачка") have no price
                if not clean(name) or not isinstance(price, (int, float)):
                    continue
                result.append((number, clean(name), float(price)))
                continue
            if pk in (None, ""):
                continue
            try:
                result.append((int(pk), clean(name), float(str(price).replace(",", "."))))
            except (TypeError, ValueError):
                raise CommandError(f"Row {number}: id {pk!r} / price {price!r} is not a number")
        workbook.close()
        return mode, result
