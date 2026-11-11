"""Text search over product names, brands and the articul (pg_trgm).

Shared by the client `product/filter/` (`q`) and the AI assistant's `search_products` tool.

The query is turned into a few variants: as typed, Latin -> Cyrillic ("podshipnik" -> "подшипник"),
Cyrillic -> Latin (for the Latin Uzbek names) and the synonyms of the `SearchSynonym` dictionary
("180203" -> "6203 2rs"). The product text and every variant are folded the same way (`fold`): lower case,
the Cyrillic letters that look like Latin ones made Latin (М6х20 = M6x20), decimal comma = dot, one apostrophe.
A product matches a variant when each word of it is in the product text or the brand name, in any order
("6203 2rs" finds "6203-2RS"); a word of 4+ letters also when it is close to a word of the text (a typo).
"""
import re

from django.contrib.postgres.lookups import TrigramWordSimilar
from django.contrib.postgres.search import TrigramWordSimilarity
from django.core.cache import cache
from django.db.models import Case, FloatField, Func, Q, TextField, Value, When
from django.db.models.functions import Concat, Greatest, Lower

from utils.slug import CYRILLIC_TO_LATIN

MAX_VARIANTS = 6
SYNONYMS_CACHE_KEY = "search:synonyms"

# a word of the query found with a typo: `text %> word`, i.e. word_similarity above
# pg_trgm.word_similarity_threshold (Postgres default 0.6); letters only, 4+
FUZZY_WORD = re.compile(r"[^\W\d_]{4,}")

# the same in SQL (TRANSLATE) and in Python
FOLD_FROM = "аекмнорстухвё×,ʻʼ‘’`"
FOLD_TO = "aekmhopctyxbex.'''''"
FOLD_TABLE = str.maketrans(FOLD_FROM, FOLD_TO)

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

WORD_SPLIT = re.compile(r"[\s\-_/\\()\[\]{}+|;:\"«»]+")
LATIN_WORD = re.compile(r"[a-z']+")
CYRILLIC = re.compile(r"[а-яёўқғҳ]")


def fold(text):
    return (text or "").lower().translate(FOLD_TABLE)


def words(text):
    return [word.strip("'.") for word in WORD_SPLIT.split(text) if word.strip("'.")]


def normalize(text):
    """The comparable form of a query / synonym: lower case, words joined by one space."""
    return " ".join(words((text or "").lower()))


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
    """Latin words (letters only, 3+) in Cyrillic; codes and sizes ("6203", "m6x20", "2rs") stay."""
    return " ".join(latin_to_cyrillic(w) if len(w) >= 3 and LATIN_WORD.fullmatch(w) else w for w in text.split())


def to_latin(text):
    return "".join(CYRILLIC_TO_LATIN.get(ch, ch) for ch in text)


def synonym_groups():
    """[[normalized term, ...], ...] of the active synonym groups (cached, dropped on every change)."""
    groups = cache.get(SYNONYMS_CACHE_KEY)
    if groups is None:
        from apps.service.models import SearchSynonym

        groups = []
        for terms in SearchSynonym.objects.filter(is_active=True).values_list("terms", flat=True):
            group = list(dict.fromkeys(term for term in (normalize(t) for t in terms or []) if term))
            if len(group) > 1:
                groups.append(group)
        cache.set(SYNONYMS_CACHE_KEY, groups, 3600)
    return groups


def query_variants(q):
    """Folded forms of `q` to look for, the typed one first."""
    base = normalize(q)
    if not base:
        return []
    forms = [base]
    padded = f" {base} "
    for group in synonym_groups():
        for term in group:
            if f" {term} " in padded:
                forms += [padded.replace(f" {term} ", f" {other} ").strip() for other in group if other != term]
    variants = []
    for form in forms:
        variants.append(form)
        if CYRILLIC.search(form):
            variants.append(normalize(to_latin(form)))
        elif LATIN_WORD.search(form):
            variants.append(to_cyrillic(form))
    return list(dict.fromkeys(fold(variant) for variant in variants))[:MAX_VARIANTS]


class Fold(Func):
    function = "TRANSLATE"
    output_field = TextField()

    def __init__(self, expression):
        super().__init__(Lower(expression), Value(FOLD_FROM), Value(FOLD_TO))


def product_search_text():
    """The folded text a product is searched by; the GIN trigram index `idx_product_search_text` is built on
    exactly this expression, so a change here needs a migration of the index."""
    return Fold(Concat("name_ru", Value(" "), "name_uz", Value(" "), "articul_code", output_field=TextField()))


def brand_names():
    from apps.service.models import Brand

    return [(pk, fold(f"{ru or ''} {uz or ''}")) for pk, ru, uz in Brand.objects.values_list("id", "name_ru", "name_uz")]


def search_products(products, q):
    """`products` that match `q`, annotated with `similarity` (higher = closer): every word found as typed
    ranks above a typo match. Not ordered: the caller orders by `-similarity` plus its own tie-breaker."""
    variants = query_variants(q)
    if not variants:
        return products.none()
    text = product_search_text()
    brands = brand_names()
    exact, found, closeness = Q(pk__in=[]), Q(pk__in=[]), []
    for variant in variants:
        variant_exact, variant_found = Q(), Q()
        for word in variant.split():
            word_q = Q(_search_text__contains=word)
            brand_ids = [pk for pk, name in brands if word in name]
            if brand_ids:
                word_q |= Q(brand_id__in=brand_ids)
            variant_exact &= word_q
            if FUZZY_WORD.fullmatch(word):
                word_q |= Q(TrigramWordSimilar(text, Value(word)))
            variant_found &= word_q
        exact |= variant_exact
        found |= variant_found
        closeness.append(TrigramWordSimilarity(Value(variant), text))
    return products.select_related("brand").alias(_search_text=text).filter(found).annotate(
        similarity=Case(When(exact, then=Value(1.0)), default=Value(0.0), output_field=FloatField())
        + (Greatest(*closeness) if len(closeness) > 1 else closeness[0]),
    )
