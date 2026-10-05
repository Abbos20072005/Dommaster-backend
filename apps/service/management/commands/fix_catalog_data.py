import re
from collections import Counter

from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, Q

from apps.base.models import Banner
from apps.service.models import (
    AddsBrands, Brand, Comment, Product, ProductAttributeValue, ProductItemCategory, ProductModel, ProductSubCategory,
)

# Mass fixes from the sheet "2. Массовые операции" of the catalog audit (BUILDEX_итоговый_план_исправлений).
# "row N" below = the row of that sheet.
# Not automated: row 4 (brand spelling style - needs a decision), rows 16-18 (barcodes, images, real stock -
# need source data). The sheet gives no replacement for row 58 ("андава") and for "VIKO PILOT" of row 14 -
# the wording here is ours.

NAME_FIELDS = ("name", "name_uz", "name_ru", "name_en")

STEPS = ("names", "brands", "category", "test-data")

BRAND_RENAME = ("Shneider", "Schneider Electric")  # row 2
BRAND_MERGE = ("AWP",)  # row 3: the same brand entered twice
MISPLACED_SUB_CATEGORY = "Сместитель для кухни"  # row 15
MISPLACED_TARGET_ITEM_CATEGORY = "Смесители для мойки"
TEST_DISCOUNT = {"pk": 670, "discount": 30, "discount_price": 700}  # row 19
# row 19: the comments ("hi", "asdasd", "Test", ...) behind the test ratings; deleted only with --delete-test-comments
TEST_COMMENT_IDS = (26, 27, 28, 29, 36, 37, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53)

# row 13: plural heads of the Onka names -> singular, as in the sheet's example
# "Блок клеммный винтовой MRK 2,5 мм² серый Onka"; a longer head goes before its prefix
ONKA_HEADS = (
    ("Блоки клеммные вставочные утроенные", "Блок клеммный вставочный утроенный"),
    ("Блоки клеммные вставочные удвоенные", "Блок клеммный вставочный удвоенный"),
    ("Блоки клеммные вставочные", "Блок клеммный вставочный"),
    ("Блоки клеммные винтовые", "Блок клеммный винтовой"),
    ("Блоки клеммные зажимные", "Блок клеммный зажимной"),
    ("Блоки предохранителя клеммовые винтовые", "Блок предохранителя клеммный винтовой"),
    ("Блоки контрольные", "Блок контрольный"),
    ("Колодки клеммные мостовые винтовые удвоенные", "Колодка клеммная мостовая винтовая удвоенная"),
    ("Колодки клеммные винтовые удвоенные", "Колодка клеммная винтовая удвоенная"),
    ("Клеммы винтовые", "Клемма винтовая"),
    ("Клеммы вставочные", "Клемма вставочная"),
    ("Клеммы с модулем", "Клемма с модулем"),
    ("Разъемы на", "Разъём на"),
)
ONKA_COLOR = re.compile(
    r"\( ?(серый|красный|желтый|зеленый|синий|оранжевый|белый|мятно-зеленый|желто-зеленый) ?\)"
)


def keep_case(source, replacement):
    if source.isupper():
        return replacement.upper()
    if source[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def replace_rule(label, pattern, replacement, literal=False):
    regex = re.compile(pattern, re.IGNORECASE)

    def rule(value):
        if literal:
            return regex.sub(replacement, value)
        return regex.sub(lambda m: keep_case(m.group(), replacement), value)

    return label, rule


def collapse_spaces(value):
    return re.sub(r"\s+", " ", value).strip()


def tidy(value):
    value = collapse_spaces(value)
    value = re.sub(r" , ?", ", ", value)
    value = re.sub(r"\( ", "(", value)
    value = re.sub(r" \)", ")", value)
    return value.strip(" ,")


def onka_singular(value):
    if not value.endswith(" Onka"):
        return value
    for plural, singular in ONKA_HEADS:
        if value.startswith(f"{plural} "):
            value = singular + value[len(plural):]
            break
    # the colour stays in brackets unless it agrees with the head: only "Блок ..." is masculine singular for sure
    if value.startswith("Блок "):
        value = ONKA_COLOR.sub(r"\1", value)
    return value


LATIN_TO_CYRILLIC = {"C": "С", "c": "с", "O": "О", "o": "о"}
CYRILLIC_TO_LATIN = {"Т": "T", "т": "t"}

SPACES_LABEL = "row 8-9: extra spaces, tabs, line breaks"

# (label, function) - applied to every product name in this order; labels are only for the report
NAME_RULES = [
    ("row 5: Cмеситель (Latin C)",
     lambda v: re.sub(r"[Cc](?=месител)", lambda m: LATIN_TO_CYRILLIC[m.group()], v, flags=re.IGNORECASE)),
    ("row 6: Oтвертка (Latin O)",
     lambda v: re.sub(r"[Oo](?=твертк)", lambda m: LATIN_TO_CYRILLIC[m.group()], v, flags=re.IGNORECASE)),
    ("row 7: STANDARТ (Cyrillic Т)",
     lambda v: re.sub(r"(?<=standar)[Тт]", lambda m: CYRILLIC_TO_LATIN[m.group()], v, flags=re.IGNORECASE)),
    ("row 13: Onka singular", onka_singular),
    ("row 14: Viko translit", lambda v: v.replace("Dif Avtomat", "Дифавтомат")
     .replace("Modulniy Puskatel", "Модульный пускатель").replace("Planka Rozetka", "Розеточная колодка")
     .replace("VIKO PILOT 6X1,5MT", "Viko Сетевой фильтр 6 гнёзд 1,5 м")),
    # "Смесительдля AWP для кухни": the glued "для" is a duplicate of the next one
    replace_rule("row 5: Смесительдля", r"месительдля(?= \S+ для\b)", "меситель"),
    replace_rule("row 5: Смесительдля", r"месительдля", "меситель для"),
    replace_rule("row 20: сверильный", r"сверильн", "сверлильн"),
    replace_rule("row 21: металличский", r"металличск", "металлическ"),
    replace_rule("row 22: внутренный", r"внутренный", "внутренний"),
    replace_rule("row 23: внутренная", r"внутренная", "внутренняя"),
    replace_rule("row 24: волтьметр", r"волтьметр", "вольтметр"),
    replace_rule("row 25: частотамер", r"частотамер", "частотомер"),
    replace_rule("row 26: испитательный", r"испитательн", "испытательн"),
    replace_rule("row 27: клемник", r"клемник", "клеммник"),
    replace_rule("row 28: разем / разьем", r"\bразь?ем", "разъём"),
    replace_rule("row 29: соеденитель", r"соеденител", "соединител"),
    replace_rule("row 30: соедение стерженей", r"соедение стерженей", "соединение стержней"),
    replace_rule("row 31: молярный", r"молярн", "малярн"),
    replace_rule("row 32: умивальник", r"умивальник", "умывальник"),
    replace_rule("row 34: ркухня", r"\bркухня\b", "кухни"),
    replace_rule("row 33: для кухня", r"для кухня\b", "для кухни"),
    replace_rule("row 35: аэрозолная", r"аэрозолн", "аэрозольн"),
    replace_rule("row 36: наждаточная", r"наждаточн", "наждачн"),
    replace_rule("row 37: средьная", r"средьная", "средняя"),
    replace_rule("row 38: шрина", r"ммшрина", "мм ширина"),
    replace_rule("row 38: шрина", r"шрина", "ширина"),
    replace_rule("row 39, 62: высого", r"\bвысого\b", "высокого"),
    replace_rule("row 40: золтыстий", r"золтыстий", "золотистый"),
    replace_rule("row 41: полифасфад", r"полифасфад", "полифосфат"),
    replace_rule("row 42: дляводы", r"дляводы", "для воды"),
    replace_rule("row 43: щить", r"\bщить\b", "щит"),
    replace_rule("row 44: винтавой", r"винтавой", "винтовой"),
    replace_rule("row 45: касой", r"\bкасой\b", "косой"),
    replace_rule("row 46: монжет", r"монжет", "манжет"),
    replace_rule("row 47: двухплосткосной", r"двухплосткосн", "двухплоскостн"),
    replace_rule("row 48: кольбасный", r"кольбасн", "колбасн"),
    replace_rule("row 50: ocean", r"\bocean\b", "OCKEAN", literal=True),
    replace_rule("row 51: шлифовальные машина", r"шлифовальные машина", "шлифовальная машина"),
    replace_rule("row 52: малинкые", r"малинкые", "маленькие"),
    replace_rule("row 53: расходомерам", r"расходомерам(?!и)", "расходомерами"),
    replace_rule("row 53: расходомерам", r"\bсрасходомерами", "с расходомерами"),
    replace_rule("row 54: нержавеющие винтами", r"нержавеющие винтами", "нержавеющими винтами"),
    replace_rule("row 55: пластиковый винтами", r"пластиковый винтами", "пластиковыми винтами"),
    replace_rule("row 56: стеклотканеваяи", r"стеклотканеваяи", "стеклотканевая"),
    replace_rule("row 57: термоусадочные трубка", r"термоусадочные трубка", "термоусадочная трубка"),
    replace_rule("row 58: андава", r"андава для жидкого обоя", "кельма для жидких обоев"),
    replace_rule("row 58: андава", r"андава для наждачная бумага", "тёрка для наждачной бумаги"),
    replace_rule("row 59: утканос", r"утканос", "утконос"),
    replace_rule("row 60: 50мт", r"(шланг сливной.*?50)\s*мт\b", r"\1 м", literal=True),
    replace_rule("row 61: кусочков", r"кусочков", "предметов"),
    replace_rule("row 63: люминар", r"люминар", "светильник"),
    replace_rule("row 64: kuller", r"\bkuller\b", "кулер"),
    replace_rule("row 65: нитьдля", r"нитьдля", "нить для"),
    replace_rule("row 66: установке", r"(?<=открытой )установке\b", "установки"),
]

BRAND_LABEL = r"(?:Бренд|Brend)\s*:"
ARTICUL_LABEL = r"(?:Артикул|Artikul)\s*:"

# "1012 (1010012) БЛОКИ КЛЕММНЫЕ ВИНТОВЫЕ MRK 2,5mm² (СЕРЫЙ)(Бренд: Onka)"
ONKA_NAME = re.compile(rf"^(\d{{4,7}}(?: ?\(\d+\))?) (.+?) ?\({BRAND_LABEL} ?Onka\)$", re.IGNORECASE)
# "(код товара - 5001) Коллектор распределительный, 2 вых x 16 мм"
PRODUCT_CODE_PREFIX = re.compile(r"^\(код товара ?- ?([^()]+)\) ?", re.IGNORECASE)
# "..., Артикул: CDB6i1C1, Бренд: DELIXI"
ARTICUL_IN_NAME = re.compile(rf" ?, ?{ARTICUL_LABEL} ?([^,()]*)", re.IGNORECASE)
# "..., Бренд: NURA" / "... (Бренд: Onka)"
BRAND_IN_NAME = re.compile(rf" ?, ?{BRAND_LABEL}[^,()]*| ?\( ?{BRAND_LABEL}[^()]*\)", re.IGNORECASE)


def clean_name(value, articul=""):
    """Returns (fixed name, articul found in the name, labels of the rules that changed something)."""
    applied = []
    if not value:
        return value, "", applied

    def apply(label, fixed):
        nonlocal value
        if fixed != value:
            applied.append(label)
            value = fixed

    apply(SPACES_LABEL, collapse_spaces(value))

    # an articul is taken out of the name only when it doesn't clash with the one the product already has
    def movable(found):
        found = found.strip()
        return found if found and articul in ("", found) else ""

    found_articul = ""

    match = ONKA_NAME.match(value)
    if match and movable(match.group(1)):
        found_articul = movable(match.group(1))
        text = re.sub(r"(?<=\d) ?mm²", " мм²", match.group(2))
        text = "".join(char.lower() if "А" <= char <= "Я" or char == "Ё" else char for char in text)
        apply("row 13: Onka code + caps", f"{text[:1].upper()}{text[1:]} Onka")

    match = PRODUCT_CODE_PREFIX.match(value)
    if match and not found_articul and movable(match.group(1)):
        found_articul = movable(match.group(1))
        apply("row 12: (код товара - N)", value[match.end():])

    match = ARTICUL_IN_NAME.search(value)
    if match and not found_articul and movable(match.group(1)):
        found_articul = movable(match.group(1))
        apply("row 11: Артикул: XXX", value[:match.start()] + value[match.end():])

    apply("row 10: Бренд: XXX", BRAND_IN_NAME.sub("", value))

    for label, rule in NAME_RULES:
        apply(label, rule(value))

    cleaned = tidy(value)
    if cleaned != value:
        value = cleaned
        if not applied:
            applied.append(SPACES_LABEL)

    return value, found_articul, applied


def named(model, name):
    condition = Q()
    for field in NAME_FIELDS:
        condition |= Q(**{f"{field}__iregex": rf"^\s*{re.escape(name)}\s*$"})
    return model.objects.rewrite(False).filter(condition).order_by("id")


class Command(BaseCommand):
    help = (
        'Mass fixes of the catalog data from the audit sheet "2. Массовые операции": product names '
        "(mixed alphabets, spaces, brand/articul inside the name, typos), brand rename and merge, "
        "the misplaced kitchen mixer sub category, test ratings and discount. Run with --dry-run first."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Do everything in a transaction and roll it back, nothing is saved.",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Print every changed product name.",
        )
        parser.add_argument(
            "--only",
            nargs="+",
            choices=STEPS,
            default=STEPS,
            help="Run only these steps (default: all).",
        )
        parser.add_argument(
            "--delete-test-comments",
            action="store_true",
            help="test-data step: also delete the test comments the test ratings come from.",
        )

    def handle(self, *args, **options):
        self.dry_run = options["dry_run"]
        self.verbose = options["verbose"]
        self.delete_test_comments = options["delete_test_comments"]

        if self.dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - everything below is rolled back at the end"))

        steps = {
            "names": self.fix_names,
            "brands": self.fix_brands,
            "category": self.fix_category,
            "test-data": self.fix_test_data,
        }
        with transaction.atomic():
            for step in STEPS:
                if step in options["only"]:
                    self.stdout.write(self.style.MIGRATE_HEADING(f"\n== {step}"))
                    steps[step]()
            if self.dry_run:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS("\nDRY RUN finished, nothing saved" if self.dry_run else "\nDone"))

    def warn(self, message):
        self.stdout.write(self.style.WARNING(f"  ! {message}"))

    # ---- rows 5-14, 20-66: product names ----

    def fix_names(self):
        # rewrite(False): work with the raw columns, modeltranslation would turn "name" into "name_<lang>"
        products = Product.objects.rewrite(False)
        stats = Counter()
        changed_products = 0
        new_articuls = 0
        clashes = 0

        for row in products.values("id", "articul_code", *NAME_FIELDS).order_by("id").iterator():
            articul = (row["articul_code"] or "").strip()
            changes = {}
            labels = set()
            for field in NAME_FIELDS:
                fixed, found_articul, applied = clean_name(row[field], articul)
                labels.update(applied)
                if fixed != row[field]:
                    changes[field] = fixed
                if found_articul and not articul:
                    articul = found_articul
                    changes["articul_code"] = found_articul
                    new_articuls += 1

            if articul and any(ARTICUL_IN_NAME.search(changes.get(f) or row[f] or "") for f in NAME_FIELDS):
                clashes += 1
                self.warn(f"product {row['id']}: articul in the name differs from articul_code {articul!r}, left as is")

            if not changes:
                continue

            changed_products += 1
            stats.update(labels)
            if self.verbose:
                for field, fixed in changes.items():
                    self.stdout.write(f"  product {row['id']} {field}: {row[field]!r} -> {fixed!r}")
            products.filter(pk=row["id"]).update(**changes)

        for label, count in sorted(stats.items(), key=lambda item: [int(n) for n in re.findall(r"\d+", item[0])[:1]]):
            self.stdout.write(f"  {label}: {count}")
        self.stdout.write(
            f"  Products changed: {changed_products}, articul_code filled: {new_articuls}, articul clashes: {clashes}"
        )

    # ---- rows 2-3: brands ----

    def fix_brands(self):
        old_name, new_name = BRAND_RENAME
        existing = named(Brand, new_name).first()
        misspelled = list(named(Brand, old_name))
        if not misspelled:
            self.stdout.write(f"  Brand {old_name!r}: 0 found, nothing to rename")
        for brand in misspelled:
            if existing:
                self.merge_brand(existing, brand)
            else:
                Brand.objects.rewrite(False).filter(pk=brand.pk).update(**{field: new_name for field in NAME_FIELDS})
                self.stdout.write(f"  Brand {brand.pk}: {old_name!r} -> {new_name!r}")
                if brand.code:
                    self.warn("the brand came from 1C - the next 1C product sync brings the old name back "
                              "until it is renamed in 1C too")
                existing = brand

        for name in BRAND_MERGE:
            brands = list(named(Brand, name).annotate(products_count=Count("product_brand")))
            if len(brands) < 2:
                self.stdout.write(f"  Brand {name!r}: {len(brands)} found, nothing to merge")
                continue
            keep = max(brands, key=lambda brand: (brand.products_count, -brand.pk))
            for brand in brands:
                if brand.pk != keep.pk:
                    self.merge_brand(keep, brand)

    def merge_brand(self, keep, duplicate):
        moved = Product.objects.filter(brand=duplicate).update(brand=keep)

        for product_model in ProductModel.objects.filter(brand=duplicate):
            same = ProductModel.objects.filter(brand=keep, name=product_model.name).first()
            if same:
                Product.objects.filter(product_model=product_model).update(product_model=same)
                product_model.delete()
            else:
                product_model.brand = keep
                product_model.save(update_fields=["brand"])

        if not AddsBrands.objects.filter(brand=keep).exists():
            AddsBrands.objects.filter(brand=duplicate).update(brand=keep)
        self.retarget_banners(duplicate, keep)

        duplicate_id = duplicate.pk
        duplicate.delete()

        # keep what the remaining brand lacks; `code` is unique, so it moves only after the delete
        filled = {
            field: getattr(duplicate, field) for field in ("code", "image")
            if getattr(duplicate, field) and not getattr(keep, field)
        }
        if filled:
            Brand.objects.filter(pk=keep.pk).update(**filled)
            for field, value in filled.items():
                setattr(keep, field, value)

        self.stdout.write(f"  Brand {duplicate_id} merged into {keep.pk} ({keep.name!r}), products moved: {moved}")
        if duplicate.code and "code" not in filled:
            self.warn(f"1C code {duplicate.code!r} of brand {duplicate_id} is gone - 1C will create the brand again "
                      f"until the two brands are merged in 1C too")

    def retarget_banners(self, old, new):
        return Banner.objects.filter(
            content_type=ContentType.objects.get_for_model(type(old)), object_id=old.pk
        ).update(content_type=ContentType.objects.get_for_model(type(new)), object_id=new.pk)

    # ---- row 15: "Сместитель для кухни" -> "Смесители для мойки" ----

    def fix_category(self):
        sub_categories = list(named(ProductSubCategory, MISPLACED_SUB_CATEGORY))
        if len(sub_categories) != 1:
            self.stdout.write(f"  Sub category {MISPLACED_SUB_CATEGORY!r}: {len(sub_categories)} found, skipped")
            return
        sub_category = sub_categories[0]

        targets = list(
            named(ProductItemCategory, MISPLACED_TARGET_ITEM_CATEGORY).exclude(product_sub_category=sub_category)
        )
        if len(targets) > 1:
            # "Сантехника" exists twice on the site - take the one next to the misplaced sub category
            targets = [
                target for target in targets
                if target.product_sub_category.product_category_id == sub_category.product_category_id
            ]
        if len(targets) != 1:
            self.warn(f"Item category {MISPLACED_TARGET_ITEM_CATEGORY!r}: {len(targets)} found, skipped")
            return
        target = targets[0]

        sub_category_id = sub_category.pk
        old_item_categories = list(ProductItemCategory.objects.filter(product_sub_category=sub_category))
        old_item_category_ids = [item_category.pk for item_category in old_item_categories]
        products = Product.objects.filter(product_item_category__in=old_item_category_ids)

        # same as the admin API: values of attributes the new category doesn't have are dropped
        ProductAttributeValue.objects.filter(product__in=products).exclude(
            attribute__category_links__item_category=target
        ).delete()
        moved = products.update(product_item_category=target)
        self.stdout.write(f"  Products moved to item category {target.pk} ({target.name!r}): {moved}")

        for item_category in old_item_categories:
            self.retarget_banners(item_category, target)
        self.retarget_banners(sub_category, target.product_sub_category)

        # Product.product_item_category is CASCADE: never delete while a product is still inside
        if Product.objects.filter(product_item_category__product_sub_category=sub_category).exists():
            self.warn(f"Sub category {sub_category_id} still has products, not deleted")
            return
        _, deleted = sub_category.delete()
        self.stdout.write(f"  Sub category {sub_category_id} deleted: {deleted}")

        # update() sends no signals
        for item_category_id in [target.pk, *old_item_category_ids]:
            cache.delete(f"product:available_filters:cat:{item_category_id}")

        self.warn(f"filters of the moved products: manage.py backfill_filter_data --item-category {target.pk}")
        if sub_category.code:
            self.warn("the sub category came from 1C - the next 1C product sync puts the products back "
                      "until they are moved in 1C too")

    # ---- row 19: test rating / discount ----

    def fix_test_data(self):
        if self.delete_test_comments:
            # one by one: the Comment signal recalculates the product rating
            comments = Comment.objects.filter(pk__in=TEST_COMMENT_IDS)
            for comment in comments:
                self.stdout.write(f"  Comment {comment.pk} of product {comment.product_id} deleted: {comment.comment!r}")
                comment.delete()

        rated =Product.objects.filter(rating__gt=0).annotate(comments=Count("product_comment"))
        without_comments = [product.pk for product in rated if not product.comments]
        with_comments = [product.pk for product in rated if product.comments]
        Product.objects.filter(pk__in=without_comments).update(rating=0, comments_quantity=0)
        self.stdout.write(f"  Rating without a single comment reset to 0: {len(without_comments)} {without_comments}")
        if with_comments:
            self.warn(f"rating kept, it comes from comments (--delete-test-comments removes the test ones): "
                      f"{with_comments}")

        cleared = Product.objects.filter(**TEST_DISCOUNT).update(discount=None, discount_price=None)
        self.stdout.write(f"  Test discount of product {TEST_DISCOUNT['pk']} cleared: {cleared}")
