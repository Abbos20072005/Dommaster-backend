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

# --by-codes: the site names were rewritten by the content team ("Авт. выкл. NEXT NXB-63 6kA 1P х-ка C 10A" in the
# list, "Автоматический выключатель модульный CHINT NEXT NXB-63 1P тип C 10A 230/400 В 6 кА" on the site), so the
# product is found by the model codes / sizes of the row: every code-like token of the row must be in the name.
LOOKALIKE = str.maketrans("авсекмнорстух", "abcekmhopctyx")  # Cyrillic letters that look Latin: С 10А = C 10A
UNIT_AFTER_NUMBER = re.compile(r"(\d)\s+(ka|a|w|bt|kbt|kw|b|v|va|kva|mm|cm|m|ma|ah|k)(?![0-9a-zа-я])")


def words(text):
    return set(re.findall(r"[0-9a-zа-яё]{2,}", clean(text).lower().replace("ё", "е")))


def tokens(text):
    """Comparable tokens of a name: '6 кА' = '6kA' = '6ka', 'NXB-63' = 'nxb63', '2,5 мм²' = '2.5mm', '25х25' = '25x25'."""
    text = clean(text).lower().replace("ё", "е").replace("²", "").replace("³", "")
    text = re.sub(r"\(\s*\d+\s*\)", " ", text)  # pack sizes: "Nura(18)"
    text = re.sub(r"(\d),(\d)", r"\1.\2", text).translate(LOOKALIKE)
    text = re.sub(r"(\d)\s*[x×*]\s*(\d)", r"\1x\2", text)
    text = re.sub(r"(?<=[0-9a-zа-я])-(?=[0-9a-zа-я])", "", text)
    text = UNIT_AFTER_NUMBER.sub(r"\1\2", text)
    # breaker curve + current, one token the product must carry: "C10" = "тип C 10A" = "х-ка C 10A" = "c10"
    text = re.sub(r"(?<![0-9a-zа-я.])([bcd])\s?(\d+)a?(?![0-9a-zа-я])", r"\1\2", text)
    text = re.sub(r"(?<![0-9a-zа-я.])(\d+(?:\.\d+)?)a(?![0-9a-zа-я])", r"\1", text)  # amps: 10A = 10
    return re.findall(r"[0-9a-zа-я]+(?:\.[0-9a-zа-я]+)*", text)


def stem(token):
    return token if any(char.isdigit() for char in token) else token[:5]


def is_code(token):
    """A token the product must carry: a model code / size ('nxb63', '10a', '0.5', '120'), not a lone digit."""
    return any(char.isdigit() for char in token) and (len(token) > 1)


def has_token(own, token):
    """The product carries the row's token: the same one, or a longer word for an abbreviation ('3клав' of
    '3-клавишный'); a short tail ('10a', '1p') must be exact."""
    if token in own:
        return True
    tail = re.search(r"[a-zа-я]+$", token)
    return bool(tail and len(tail.group()) >= 3 and any(other.startswith(token) for other in own))


def has_word(stems, word):
    """'выкл' of 'выключатель': a row word is the start of a product word (both cut to 5 letters)."""
    return any(other.startswith(word) for other in stems)


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
        parser.add_argument("--by-codes", action="store_true",
                            help="Price list: a row without an articul / exact name is matched by its model codes "
                                 "and sizes (every one must be in the product name; needs --brand).")
        parser.add_argument("--report", help="Write every row with its product and prices to this .xlsx.")
        parser.add_argument("--dry-run", action="store_true", help="Roll everything back at the end.")

    def handle(self, *args, **options):
        mode, rows = self.read_rows(options["file"], options["sheet"])
        if mode == "id" and not options["usd_rate"]:
            raise CommandError("--usd-rate is required for a sheet of product ids and dollar prices")
        if options["by_codes"] and not options["brand"]:
            raise CommandError("--by-codes needs --brand: codes alone are not enough across the whole catalog")
        report = []
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
                matched = self.match_by_name(rows, options["brand"], options["by_codes"], factor)
            for product, name, value, row in matched:
                if not product:
                    missing.append(row)
                    report.append((row, name, value, round_price_up(value * factor), None))
                    continue
                report.append((row, name, value, round_price_up(value * factor), product))
                if mode == "id" and name and clean(name).lower() != clean(product.name_ru).lower():
                    renamed.append((product.pk, name, product.name_ru))
                exact = value * factor
                price = round_price_up(exact)
                if product.discount_price:
                    discounted.append((product.pk, product.discount_price))
                if product.product_code:
                    one_c.append(product.pk)
                # prices are stored rounded up to 100 so'm (Product.save): 35503.95 -> 35600
                report[-1] += (product.price,)
                if product.price == price:
                    same += 1
                    continue
                if product.price and abs(price - product.price) / product.price > BIG_CHANGE:
                    big.append((product.pk, product.price, price))
                    if options["by_codes"]:
                        # a pack on the site and a piece in the list (560 pcs: 186300 vs 600) - a person decides
                        report[-1] = report[-1][:-1] + (product.price, "big")
                        continue
                self.stdout.write(f"  {product.pk} {product.name_ru!r}: {product.price or 0:.0f} -> {price:.0f}"
                                  + ("" if product.is_active else "  (hidden)"))
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
            self.warn(f"{pk}: {old:.0f} -> {new:.0f} is a change of more than {BIG_CHANGE:.0%} - "
                      + ("NOT applied (--by-codes), set it by hand" if options["by_codes"] else "check the row"))
        if discounted:
            self.warn("discount_price set (the cart charges it, not the new price): "
                      + ", ".join(f"{pk} ({price:.0f})" for pk, price in discounted))
        if one_c:
            self.warn(f"{len(one_c)} products have a 1C code: 1C sets the price again when it re-sends the card")
        if options["report"]:
            self.write_report(options["report"], report)
            self.stdout.write(f"  report: {options['report']}")
        self.stdout.write(self.style.SUCCESS("DRY RUN finished, nothing saved" if options["dry_run"] else "Done"))

    def match_by_name(self, rows, brand_name, by_codes=False, factor=1):
        """[(product or None, name, price, row label)] - a product taken by two rows is skipped in both
        (unless they give it the same price)."""
        products = Product.objects.select_for_update()
        brand = None
        if brand_name:
            brand = Brand.objects.filter(name__iexact=brand_name).first()
            if not brand:
                raise CommandError(f"No brand {brand_name!r}")
            products = products.filter(brand=brand)
        coded = self.coded_products(products, brand) if by_codes else None
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
            if not candidates and coded is not None:
                product, why = self.match_by_codes(name, coded)
                if not product:
                    label += f" - {why}"
                result.append((product, name, value, label))
                continue
            if len(candidates) > 1:
                # one articul for several products (the sheet's slip: KARE / NEW BUBBLE / VERTICAL LINE) →
                # the one whose name shares the most words with the row
                sheet_words = words(name)
                scored = sorted(((len(sheet_words & words(p.name_ru)), p) for p in candidates),
                                key=lambda item: -item[0])
                candidates = [scored[0][1]] if scored[0][0] > scored[1][0] else []
            result.append((candidates[0] if candidates else None, name, value, label))
        taken = {}
        for product, name, value, label in result:
            if product:
                taken.setdefault(product.pk, set()).add(round_price_up(value * factor))
        seen, final = set(), []
        for product, name, value, label in result:
            if product and len(taken[product.pk]) > 1:
                final.append((None, name, value, f"{label} - the same product {product.pk} as another row "
                                                 f"with another price"))
            elif product and product.pk in seen:  # the same row twice in the list (two sections)
                final.append((None, name, value, f"{label} - product {product.pk} already priced by another row"))
            else:
                if product:
                    seen.add(product.pk)
                final.append((product, name, value, label))
        return final

    @staticmethod
    def coded_products(products, brand):
        ignored = set(tokens(brand.name)) | {"electric", "electro"}
        result = []
        for product in products:
            own = tokens(" ".join(filter(None, [product.name_ru, product.articul_code, product.product_code])))
            stems = {stem(token) for token in own} - ignored
            if stems:
                result.append((product, set(own), stems, ignored))
        return result

    @staticmethod
    def match_by_codes(name, coded):
        """(product, None) or (None, why). Every code of the row must be a token of the product; the product whose
        name is covered best by the row wins, a tie is not a match."""
        row = tokens(name)
        if not coded:
            return None, "no products of the brand"
        ignored = coded[0][3]
        codes = {token for token in row if is_code(token)} - ignored
        row_stems = {stem(token) for token in row} - ignored
        row_words = {stem(token) for token in row if token.isalpha() and len(token) >= 3} - ignored
        scored = []
        for product, own, stems, _ in coded:
            if not all(has_token(own, token) for token in codes):
                continue
            found = {word for word in row_words if has_word(stems, word)}
            if row_words and not found:
                continue  # same sizes, another kind of goods
            if not codes and (len(row_words) < 2 or found != row_words):
                continue  # nothing but words: all of them must be in the name
            covered = sum(1 for other in stems if other in row_stems or any(other.startswith(word) for word in found))
            scored.append((covered / len(stems), product))
        if not scored:
            return None, "no product with these codes"
        scored.sort(key=lambda item: -item[0])
        if len(scored) > 1 and scored[0][0] == scored[1][0]:
            return None, f"not sure: {scored[0][1].pk} / {scored[1][1].pk}"
        return scored[0][1], None

    @staticmethod
    def write_report(path, report):
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(["Строка", "Наименование (прайс)", "Цена прайса", "Новая цена", "ID", "Наименование (сайт)",
                      "Старая цена", "Активен", "Итог"])
        for row, name, value, price, product, *old in report:
            old, flag = (old + [None, None])[:2]
            if not product:
                result = row.split(" - ", 1)[1] if " - " in row else "не найден"
            elif flag == "big":
                result = f"разница больше {BIG_CHANGE:.0%} - не применена, проверить"
            else:
                result = "та же цена" if old == price else "изменена"
            sheet.append([row.split(" ")[1] if row.startswith("row ") else row, name, value, price,
                          product.pk if product else None, product.name_ru if product else None, old,
                          ("да" if product.is_active else "нет") if product else None, result])
        workbook.save(path)

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
            if find(LIST_PRICE_COLUMNS) is not None:
                name_column = find(LIST_NAME_COLUMNS)
                if name_column is None:
                    # the header split over two rows / no name header ("№ | Подразетники" under "ед.изм. | цена"):
                    # the name is the column before the unit, the unit the one before the price
                    name_column = (find(("цена",)) if find(("цена",)) is not None else find(LIST_PRICE_COLUMNS)) - 2
                if name_column >= 0:
                    mode, columns = "list", [None, name_column, find(LIST_PRICE_COLUMNS)]
                    break
        else:
            raise CommandError(f"No header row with the columns {ID_COLUMNS} + {PRICE_COLUMNS} "
                               f"or {LIST_NAME_COLUMNS} + {LIST_PRICE_COLUMNS}")

        result = []
        for number, row in rows:
            pk, name, price = (row[index] if index is not None and index < len(row) else None for index in columns)
            if mode == "list":
                # section titles ("Арматура для бачка") have no price
                if not clean(name) or not isinstance(price, (int, float)) or price <= 0:
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
