from django.utils.text import slugify

# Russian + Uzbek cyrillic -> latin, so slugs stay ASCII
CYRILLIC_TO_LATIN = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "j", "з": "z", "и": "i", "й": "y",
    "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f",
    "х": "x", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sh", "ъ": "", "ы": "i", "ь": "", "э": "e", "ю": "yu",
    "я": "ya", "ў": "o", "қ": "q", "ғ": "g", "ҳ": "h",
}


def slugify_latin(text):
    text = "".join(CYRILLIC_TO_LATIN.get(ch, ch) for ch in str(text or "").lower())
    return slugify(text)


def unique_slug(model, text, exclude_pk=None, fallback="item"):
    """Slug from `text`, unique within `model` (`-2`, `-3`, ... suffix on collision)."""
    max_length = model._meta.get_field("slug").max_length
    # leave room for the "-N" suffix
    base = slugify_latin(text)[:max_length - 8].strip("-") or fallback
    queryset = model._default_manager.exclude(pk=exclude_pk)
    slug, n = base, 1
    while queryset.filter(slug=slug).exists():
        n += 1
        slug = f"{base}-{n}"
    return slug
