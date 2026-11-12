"""Text search over product names, brands and codes (pg_trgm).

Shared by the client `product/filter/` (`q`), the `search/` suggestions and the AI assistant's
`search_products` tool.

The query is looked for in a few forms (`query_variants`): as typed, Cyrillic -> Uzbek Latin
("қувур" -> "quvur", "кафел елими" -> "kafel yelimi"; the names are Latin in uz) and Latin -> Cyrillic
("laminat" -> "ламинат"; most names exist only in ru). A query that looks like a code ("ai91303",
"LC1D09M7") is also compared with the articul / 1C code (case, spaces and dashes ignored) and the barcode.

`relevance` tells how well a found product fits: the share of the query words in its text. The trigram
similarity alone also finds names that only share a few letters ("boyler" -> "otboy bolg'a"), so the
assistant keeps only the products that carry the words of the query.
"""
import re
from difflib import SequenceMatcher

from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Case, F, FloatField, Func, Q, Value, When
from django.db.models.functions import Coalesce, Greatest, Lower

# a product is found when any of its names is at least this similar to the query, or its brand name at least
# MIN_BRAND_SIMILARITY: brand names are short, so a few shared letters already gave 0.2 and every product of
# the brand ("boyler" -> all 88 of Boou); a misspelt brand ("bosh" / "bosch" 0.375) still passes
MIN_SIMILARITY = 0.155
MIN_BRAND_SIMILARITY = 0.35
NAME_FIELDS = ("name", "name_uz", "name_ru")
BRAND_FIELDS = ("brand__name", "brand__name_uz", "brand__name_ru")

UZ_CYRILLIC_TO_LATIN = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "j", "з": "z", "и": "i",
    "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
    "у": "u", "ф": "f", "х": "x", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sh", "ъ": "'", "ы": "i", "ь": "",
    "э": "e", "ю": "yu", "я": "ya", "ў": "o'", "қ": "q", "ғ": "g'", "ҳ": "h",
}
CYRILLIC_VOWELS = set("аеёиоуўыэюя")

LATIN_TO_CYRILLIC = {
    "shch": "щ", "sch": "щ", "sh": "ш", "ch": "ч", "zh": "ж", "kh": "х", "ts": "ц",
    "ya": "я", "yu": "ю", "yo": "ё", "ye": "е",
    "a": "а", "b": "б", "c": "ц", "d": "д", "e": "е", "f": "ф", "g": "г", "h": "х", "i": "и", "j": "ж", "k": "к",
    "l": "л", "m": "м", "n": "н", "o": "о", "p": "п", "q": "к", "r": "р", "s": "с", "t": "т", "u": "у", "v": "в",
    "w": "в", "x": "х", "z": "з",
}
LATIN_KEY_LENGTHS = (4, 3, 2, 1)
LATIN_VOWELS = set("aeiouy")
# "-iy" / "-yy" at the end of a word: ий after these, else ый ("klemmniy" -> клеммный, "metallicheskiy" -> -ский)
SOFT_ENDING_AFTER = ("k", "g", "h")

APOSTROPHES = str.maketrans({ch: "'" for ch in "ʻʼ‘’`´"})
CYRILLIC = re.compile(r"[а-яёўқғҳ]")
LATIN_WORD = re.compile(r"[a-z']+")
WORD = re.compile(r"[\w']+")
# a code: one word with a digit, letters / digits / dashes / dots only ("ai91303", "LC1D09M7", "1047-1010047")
CODE = re.compile(r"(?=.*\d)[\w\-./]{4,}")
CODE_JUNK = re.compile(r"[^0-9a-zа-яё]")
CODE_JUNK_SQL = "[^0-9a-zа-яё]"
# "600х300", "3×2,5", "10*20" -> "600x300", "3x2.5", "10x20"
SIZE_X = re.compile(r"(?<=\d)\s*[xх×*]\s*(?=\d)")
DECIMAL_COMMA = re.compile(r"(?<=\d),(?=\d)")

# relevance of a query word found in the product text: the whole word / its stem (an ending changed:
# "двери" in "дверь") / a word of the text spelled close to it (a typo)
WORD_FOUND, STEM_FOUND, TYPO_FOUND = 1.0, 0.8, 0.7
TYPO_RATIO = 0.8
TYPO_MIN_LENGTH = 5


def normalize(text):
    """Lower case, one apostrophe, sizes and decimals spelled one way, words joined by one space.
    (ё stays: the Uzbek Latin of "бўёқ" is "bo'yoq".)"""
    text = str(text or "").lower().translate(APOSTROPHES)
    text = DECIMAL_COMMA.sub(".", SIZE_X.sub("x", text))
    return " ".join(text.split())


def to_uz_latin(text):
    out = []
    for i, ch in enumerate(text):
        if ch == "е" and (i == 0 or not text[i - 1].isalpha() or text[i - 1] in CYRILLIC_VOWELS):
            out.append("ye")   # ертўла -> yerto'la, but белгилаш -> belgilash
        else:
            out.append(UZ_CYRILLIC_TO_LATIN.get(ch, ch))
    return "".join(out)


def latin_to_cyrillic(word):
    word = word.replace("'", "")
    ending = ""
    if len(word) > 4 and word[-2:] in ("iy", "yy", "ij"):
        word, ending = word[:-2], "ий" if word[:-2].endswith(SOFT_ENDING_AFTER) else "ый"
    out, i = [], 0
    while i < len(word):
        if word[i] == "y" and word[i + 1:i + 2] not in ("a", "u", "o", "e"):
            # after a consonant ы ("vyklyuchatel"), else й ("kley")
            out.append("ы" if i and word[i - 1] not in LATIN_VOWELS else "й")
            i += 1
            continue
        for size in LATIN_KEY_LENGTHS:
            part = word[i:i + size]
            if len(part) == size and part in LATIN_TO_CYRILLIC:
                out.append(LATIN_TO_CYRILLIC[part])
                i += size
                break
        else:
            out.append(word[i])
            i += 1
    return "".join(out) + ending


def to_cyrillic(text):
    """Latin words (letters only, 3+) in Cyrillic; codes and sizes ("m6x20", "600x300") stay."""
    return " ".join(latin_to_cyrillic(w) if len(w) >= 3 and LATIN_WORD.fullmatch(w) else w for w in text.split())


def query_variants(q):
    """The forms of `q` to look for, the typed one first."""
    base = normalize(q)
    if not base:
        return []
    variants = [base]
    if CYRILLIC.search(base):
        variants.append(to_uz_latin(base))
    elif any(len(w) >= 3 and LATIN_WORD.fullmatch(w) for w in base.split()):
        variants.append(to_cyrillic(base))
    return list(dict.fromkeys(variants))


def code_of(text):
    """A code compared without case, spaces, dashes and dots."""
    return CODE_JUNK.sub("", str(text or "").lower())


def is_code(q):
    q = str(q or "").strip()
    return bool(CODE.fullmatch(q)) and len(code_of(q)) >= 4


class CodeOf(Func):
    """`code_of` in SQL."""
    function = "REGEXP_REPLACE"

    def __init__(self, field):
        super().__init__(Lower(Coalesce(field, Value(""))), Value(CODE_JUNK_SQL), Value(""), Value("g"))


def search_products(products, q):
    """`products` that match `q`, annotated with `similarity` (the best of the names / brand names over the
    query variants; 1 for a code match).

    Not ordered: the caller orders by `-similarity` plus its own tie-breaker.
    """
    variants = query_variants(q)
    if not variants:
        return products.none()
    name_similarities, brand_similarities, found = [], [], Q()
    for i, variant in enumerate(variants):
        if not i:
            names, brands = NAME_FIELDS, BRAND_FIELDS
        elif CYRILLIC.search(variant):
            names, brands = ("name_ru",), ()           # Latin typed -> the ru names
        else:
            names, brands = ("name_uz",), ("brand__name",)  # Cyrillic typed -> the Latin uz names, brands
        for field in names:
            name_similarities.append(TrigramSimilarity(field, variant))
        for field in brands:
            brand_similarities.append(TrigramSimilarity(field, variant))
        for field in names + brands:
            found |= Q(**{f"{field}__icontains": variant})
    products = products.select_related("brand").alias(
        _name_similarity=Greatest(*name_similarities), _brand_similarity=Greatest(*brand_similarities))
    code = Q(pk__in=[])
    if is_code(q):
        key = code_of(q)
        products = products.alias(_articul=CodeOf("articul_code"), _code=CodeOf("product_code"))
        code = Q(_articul__contains=key) | Q(_code__contains=key) | Q(barcode=str(q).strip())
    return products.filter(
        Q(_name_similarity__gt=MIN_SIMILARITY) | Q(_brand_similarity__gt=MIN_BRAND_SIMILARITY) | found | code,
    ).annotate(
        similarity=Case(
            When(code, then=Value(1.0)),
            default=Greatest(F("_name_similarity"), F("_brand_similarity")),
            output_field=FloatField(),
        ),
    )


def product_text(product):
    """What the relevance of `product` is measured on: its names, brand names and codes."""
    brand = product.brand if product.brand_id else None
    parts = [
        product.name_ru, product.name_uz, product.articul_code, product.product_code,
        brand and brand.name_ru, brand and brand.name_uz,
    ]
    return normalize(" ".join(part for part in parts if part))


def _stem(word):
    if len(word) >= 8:
        return word[:-2]
    if len(word) >= 5:
        return word[:-1]
    return word


def _word_score(word, text, text_words):
    if word in text_words or (len(word) >= 3 and word in text):
        return WORD_FOUND
    stem = _stem(word)
    if stem != word and any(w.startswith(stem) for w in text_words):
        return STEM_FOUND
    if len(word) >= TYPO_MIN_LENGTH and word.isalpha() and any(
            SequenceMatcher(None, word, w).ratio() >= TYPO_RATIO for w in text_words if abs(len(w) - len(word)) <= 2):
        return TYPO_FOUND
    return 0.0


def word_forms(word):
    """A query word as typed and in the other script."""
    if CYRILLIC.search(word):
        return [word, to_uz_latin(word)]
    if len(word) >= 3 and LATIN_WORD.fullmatch(word):
        return [word, latin_to_cyrillic(word)]
    return [word]


def relevance(q, text):
    """0..1: how much of `q` is in `text` (a `product_text`) — the mean score of the query words, each in its
    best script ("Dusel lampa" = Dusel + лампа); 1 when a code query is the product's code."""
    text = normalize(text)
    text_words = set(WORD.findall(text))
    if is_code(q) and code_of(q) in code_of(text):
        return 1.0
    words = WORD.findall(normalize(q))
    if not words:
        return 0.0
    score = sum(max(_word_score(form, text, text_words) for form in word_forms(word)) for word in words)
    return round(score / len(words), 2)
