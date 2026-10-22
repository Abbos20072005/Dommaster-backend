from django.utils.text import slugify

# Russian + Uzbek cyrillic -> latin: the table agreed for the site URLs (BLD-243 / BLD-47 — ж -> zh, ы -> y,
# х -> h, ц -> ts, щ -> sch, ъ / ь dropped). Every live URL comes out of it, so a changed letter moves every
# slug built from it: don't touch it without the SEO plan, and rebuild the slugs after
# (`manage.py backfill_seo_slugs --rebuild`, old slugs go to SlugHistory -> 301).
CYRILLIC_TO_LATIN = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "zh", "з": "z", "и": "i", "й": "y",
    "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f",
    "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu",
    "я": "ya", "ў": "o", "қ": "q", "ғ": "g", "ҳ": "h",
}

# room left for the "-N" / "-<id>" uniqueness suffix
SUFFIX_ROOM = 8


def slugify_latin(text):
    text = "".join(CYRILLIC_TO_LATIN.get(ch, ch) for ch in str(text or "").lower())
    return slugify(text)


def slug_base(model, text, field="slug", fallback="item", reserve=SUFFIX_ROOM):
    """Slug from `text`, cut to fit the column with `reserve` characters left for a suffix.

    For callers that make the slug unique themselves (an `-<id>` suffix, or a mass rebuild that dedupes
    the new values in memory instead of querying per row).
    """
    max_length = model._meta.get_field(field).max_length
    return slugify_latin(text)[:max_length - reserve].strip("-") or fallback


def unique_slug(model, text, exclude_pk=None, fallback="item"):
    """Slug from `text`, unique within `model` (`-2`, `-3`, ... suffix on collision)."""
    return unique_slug_for(model, text, field="slug", exclude_pk=exclude_pk, fallback=fallback)


def unique_slug_for(model, text, field="slug", exclude_pk=None, fallback="item"):
    """Slug from `text`, unique within `model` on the given column (`-2`, `-3`, ... on collision).

    `field` lets a per-language slug (`slug_uz` / `slug_ru`) be made unique within its own column.
    """
    base = slug_base(model, text, field=field, fallback=fallback)
    queryset = model._default_manager.exclude(pk=exclude_pk)
    slug, n = base, 1
    while queryset.filter(**{field: slug}).exists():
        n += 1
        slug = f"{base}-{n}"
    return slug


def slug_with_id(model, text, pk, field="slug", fallback="item"):
    """`<name>-<pk>` — unique by construction, so no collision query (products: a mass backfill of tens of
    thousands of rows stays cheap, and the slug of a product with a repeated name is predictable)."""
    suffix = f"-{pk}"
    return slug_base(model, text, field=field, fallback=fallback, reserve=len(suffix)) + suffix
