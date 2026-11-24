"""FAQ: answer HTML cleaning + the cached client list (`GET /api/v1/faq/`)."""
import re
from html import escape
from html.parser import HTMLParser
from django.conf import settings
from django.core.cache import cache
from django.db.models import Prefetch

ALLOWED_TAGS = {"a", "b", "strong", "ul", "ol", "li", "p", "br"}
VOID_TAGS = {"br"}
# dropped together with their text
DROP_CONTENT_TAGS = {"script", "style", "iframe", "object", "embed", "template", "noscript", "textarea", "title",
                     "svg", "math", "head"}
LINK_PREFIXES = ("http://", "https://", "mailto:", "tel:")
CONTROL_CHARS = re.compile(r"[\x00-\x20\x7f]")

CACHE_TTL = 15 * 60


def safe_href(value):
    compact = CONTROL_CHARS.sub("", value or "").lower()
    if compact.startswith(LINK_PREFIXES) or (compact.startswith("/") and not compact.startswith("//")):
        return value.strip()
    return None


class AnswerCleaner(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.open = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in DROP_CONTENT_TAGS:
            self.skip += 1
            return
        if self.skip or tag not in ALLOWED_TAGS:
            return
        if tag == "a":
            href = safe_href(dict(attrs).get("href"))
            if href is None:
                self.out.append("<a>")
            else:
                self.out.append(f'<a href="{escape(href, quote=True)}" rel="noopener noreferrer">')
        else:
            self.out.append(f"<{tag}>")
        if tag not in VOID_TAGS:
            self.open.append(tag)

    def handle_startendtag(self, tag, attrs):
        if tag in VOID_TAGS:
            self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag in DROP_CONTENT_TAGS:
            self.skip = max(self.skip - 1, 0)
            return
        if self.skip or tag not in self.open:
            return
        while self.open:
            last = self.open.pop()
            self.out.append(f"</{last}>")
            if last == tag:
                break

    def handle_data(self, data):
        if not self.skip:
            self.out.append(escape(data, quote=False))

    def result(self):
        self.close()
        return "".join(self.out) + "".join(f"</{tag}>" for tag in reversed(self.open))


def clean_answer(value):
    """Keeps links (http / https / mailto / tel / site path), bold, lists, paragraphs and line breaks;
    every other tag and every attribute but `href` is dropped, script / style go with their text."""
    cleaner = AnswerCleaner()
    cleaner.feed(value or "")
    return cleaner.result().strip()


def has_text(value):
    return bool(re.sub(r"<[^>]*>|&nbsp;|\s", "", value or ""))


def cache_key(language, page):
    return f"faq:{language}:{page or 'all'}"


def clear_cache():
    from apps.base.models import FaqItem
    cache.delete_many([cache_key(language, page) for language in settings.MODELTRANSLATION_LANGUAGES
                       for page in (None, *FaqItem.PAGE_KEYS)])


def active_topics(page=None):
    """Active topics with their active questions (`topic.questions`), position order; with `page` only the
    questions shown on that page and only the topics that have one."""
    from apps.base.models import FaqItem, FaqTopic
    items = FaqItem.objects.filter(is_active=True).order_by("position", "id")
    if page:
        items = items.filter(page_keys__contains=[page])
    topics = FaqTopic.objects.filter(is_active=True).prefetch_related(
        Prefetch("items", queryset=items, to_attr="questions"))
    if page:
        topics = topics.filter(items__in=items).distinct()
    return list(topics.order_by("position", "id"))
