"""Product feeds for the marketplaces: Google Merchant Center (RSS 2.0 with `g:` fields) and Yandex (YML).

Both are files under MEDIA_ROOT/feeds/, rebuilt by Celery beat (`tasks.build_merchant_feeds`, every 6 hours)
and served by `MerchantFeedViewSet` (`feeds/google.xml`, `feeds/yandex.yml`). The price is the one the cart
charges (`discount_price` when set, else `price`), so the feed, the site and the page markup show the same number.
Texts are ru. Links: `SITE_URL` + PRODUCT_PATH, images: `BACKEND_URL` + the media path — without them the
feeds are not built.
"""
import html
import logging
import os
import re
import tempfile
from datetime import datetime
from xml.sax.saxutils import escape, quoteattr
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import Exists, OuterRef, Prefetch
from django.utils.html import strip_tags

from .models import Product, ProductImage, ProductCategory, ProductSubCategory, ProductItemCategory

logger = logging.getLogger(__name__)

FEEDS_DIR = "feeds"
GOOGLE_FILE = "google.xml"
YANDEX_FILE = "yandex.yml"
# the product page of the site (agree with the frontend before changing)
PRODUCT_PATH = "/product/{id}"
SHOP_NAME = "Dommaster"
CURRENCY = "UZS"
MAX_IMAGES = 10  # main + 9 more: the limit of both formats
GOOGLE_TITLE_MAX = 150
GOOGLE_DESCRIPTION_MAX = 5000
YANDEX_DESCRIPTION_MAX = 3000
# Yandex category ids are one number space: the three levels of our tree are put apart by these offsets
YANDEX_CATEGORY_OFFSET = {"category": 1_000_000_000, "sub": 2_000_000_000, "item": 3_000_000_000}
CHUNK = 2000


class FeedConfigError(Exception):
    """SITE_URL / BACKEND_URL are not set: links of the feed would lead nowhere."""


def feed_path(name):
    return os.path.join(settings.MEDIA_ROOT, FEEDS_DIR, name)


def feed_products():
    """What goes into the feeds: active, with a price and a picture. Out of stock ones stay (out_of_stock)."""
    images = Prefetch("product_image", queryset=ProductImage.objects.order_by("position", "id"))
    return Product.objects.filter(is_active=True, price__gt=0).filter(
        Exists(ProductImage.objects.filter(product_id=OuterRef("pk")))
    ).select_related(
        "brand", "product_item_category__product_sub_category__product_category",
    ).prefetch_related(images).order_by("id")


# ---- values ----

def final_price(product):
    """What the cart charges for the product (`Cart` totals: discount_price when it is set)."""
    return product.discount_price if product.discount_price is not None else product.price


def format_price(value):
    """150000 / 150000.5: whole sums without decimals, as the site shows them."""
    value = round(float(value), 2)
    return str(int(value)) if value == int(value) else f"{value:.2f}"


def plain_text(rich, limit):
    """Rich text of the admin panel / 1C without tags and entities, whitespace collapsed."""
    # paragraphs / line breaks become spaces, or "провод.Автоматы" sticks together
    text = re.sub(r"<(br|/p|/div|/li|/h[1-6]|/tr|/td)\b[^>]*>", " ", rich or "", flags=re.I)
    text = html.unescape(strip_tags(text)).replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        text = text[:limit - 1].rstrip() + "…"
    return text


def valid_gtin(code):
    """A barcode Google accepts as GTIN: 8 / 12 / 13 / 14 digits with a correct check digit
    (1C barcodes are often internal codes — a wrong GTIN gets the item disapproved, none does not)."""
    code = (code or "").strip()
    if not code.isdigit() or len(code) not in (8, 12, 13, 14):
        return None
    digits = [int(d) for d in code]
    total = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(digits[:-1])))
    return code if (10 - total % 10) % 10 == digits[-1] else None


def product_data(product, site_url, backend_url):
    """One product in the shape both writers use, or None when it can't be listed."""
    price = final_price(product)
    images = [backend_url + image.image.url for image in product.product_image.all() if image.image][:MAX_IMAGES]
    if not price or price <= 0 or not images:
        return None
    name = (product.name_ru or product.name or "").strip()
    if not name:
        return None
    item = product.product_item_category
    sub = item.product_sub_category if item else None
    category = sub.product_category if sub else None
    brand = product.brand
    return {
        "id": str(product.id),
        "name": name,
        "description": product.description_ru or product.description or product.short_description_ru or "",
        "url": site_url + PRODUCT_PATH.format(id=product.id),
        "images": images,
        "price": price,
        # the crossed-out price: only when the cart really charges less
        "old_price": product.price if price < product.price else None,
        "available": product.quantity > 0,
        "brand": ((brand.name_ru or brand.name or "").strip() if brand else ""),
        "mpn": (product.articul_code or "").strip(),
        "barcode": (product.barcode or "").strip(),
        "categories": [c for c in (category, sub, item) if c],
    }


def category_name(category):
    return (category.name_ru or category.name or "").strip()


# ---- writers ----

def google_item(data):
    title = data["name"][:GOOGLE_TITLE_MAX]
    description = plain_text(data["description"], GOOGLE_DESCRIPTION_MAX) or title
    rows = [
        ("g:id", data["id"]),
        ("g:title", title),
        ("g:description", description),
        ("g:link", data["url"]),
        ("g:image_link", data["images"][0]),
        *[("g:additional_image_link", url) for url in data["images"][1:]],
        ("g:availability", "in_stock" if data["available"] else "out_of_stock"),
        ("g:condition", "new"),
    ]
    if data["old_price"] is not None:
        rows += [("g:price", f"{format_price(data['old_price'])} {CURRENCY}"),
                 ("g:sale_price", f"{format_price(data['price'])} {CURRENCY}")]
    else:
        rows.append(("g:price", f"{format_price(data['price'])} {CURRENCY}"))
    gtin = valid_gtin(data["barcode"])
    if data["brand"]:
        rows.append(("g:brand", data["brand"]))
    if gtin:
        rows.append(("g:gtin", gtin))
    if data["mpn"]:
        rows.append(("g:mpn", data["mpn"]))
    # Google wants GTIN or brand + MPN; a product with neither says so instead of being disapproved
    if not gtin and not (data["brand"] and data["mpn"]):
        rows.append(("g:identifier_exists", "no"))
    if data["categories"]:
        rows.append(("g:product_type", " > ".join(category_name(c) for c in data["categories"])))
    body = "".join(f"<{tag}>{escape(str(value))}</{tag}>" for tag, value in rows)
    return f"<item>{body}</item>\n"


def write_google(out, products, site_url):
    out.write('<?xml version="1.0" encoding="UTF-8"?>\n'
              '<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">\n<channel>\n'
              f"<title>{escape(SHOP_NAME)}</title><link>{escape(site_url)}</link>"
              f"<description>{escape(SHOP_NAME)}</description>\n")
    count = 0
    for data in products:
        out.write(google_item(data))
        count += 1
    out.write("</channel>\n</rss>\n")
    return count


def yandex_category_id(category):
    if isinstance(category, ProductCategory):
        return YANDEX_CATEGORY_OFFSET["category"] + category.id
    if isinstance(category, ProductSubCategory):
        return YANDEX_CATEGORY_OFFSET["sub"] + category.id
    return YANDEX_CATEGORY_OFFSET["item"] + category.id


def yandex_offer(data):
    rows = [
        ("url", data["url"]),
        ("price", format_price(data["price"])),
    ]
    if data["old_price"] is not None:
        rows.append(("oldprice", format_price(data["old_price"])))
    rows.append(("currencyId", CURRENCY))
    if data["categories"]:
        rows.append(("categoryId", yandex_category_id(data["categories"][-1])))
    rows += [("picture", url) for url in data["images"]]
    rows += [("delivery", "true"), ("pickup", "true"), ("name", data["name"])]
    if data["brand"]:
        rows.append(("vendor", data["brand"]))
    if data["mpn"]:
        rows.append(("vendorCode", data["mpn"]))
    description = plain_text(data["description"], YANDEX_DESCRIPTION_MAX)
    if description:
        rows.append(("description", description))
    gtin = valid_gtin(data["barcode"])
    if gtin:
        rows.append(("barcode", gtin))
    body = "".join(f"<{tag}>{escape(str(value))}</{tag}>" for tag, value in rows)
    available = "true" if data["available"] else "false"
    return f'<offer id={quoteattr(data["id"])} available="{available}">{body}</offer>\n'


def write_yandex(out, products, site_url):
    """YML wants the categories before the offers: the offers are collected first (a few MB at most)."""
    offers, categories = [], {}
    for data in products:
        offers.append(yandex_offer(data))
        for category in data["categories"]:
            categories[yandex_category_id(category)] = category
    now = datetime.now(ZoneInfo(settings.TIME_ZONE)).isoformat(timespec="minutes")
    out.write('<?xml version="1.0" encoding="UTF-8"?>\n'
              f'<yml_catalog date="{now}">\n<shop>\n'
              f"<name>{escape(SHOP_NAME)}</name><company>{escape(SHOP_NAME)}</company>"
              f"<url>{escape(site_url)}</url>\n"
              f'<currencies><currency id="{CURRENCY}" rate="1"/></currencies>\n<categories>\n')
    for category_id in sorted(categories):
        category = categories[category_id]
        parent = None
        if isinstance(category, ProductSubCategory):
            parent = yandex_category_id(category.product_category)
        elif isinstance(category, ProductItemCategory):
            parent = yandex_category_id(category.product_sub_category)
        parent_attr = f' parentId="{parent}"' if parent else ""
        out.write(f'<category id="{category_id}"{parent_attr}>{escape(category_name(category))}</category>\n')
    out.write("</categories>\n<offers>\n")
    out.writelines(offers)
    out.write("</offers>\n</shop>\n</yml_catalog>\n")
    return len(offers)


# ---- build ----

def urls():
    site_url = (getattr(settings, "SITE_URL", "") or "").rstrip("/")
    backend_url = (settings.BACKEND_URL or "").rstrip("/")
    if not site_url or not backend_url:
        raise FeedConfigError("SITE_URL and BACKEND_URL must be set to build the product feeds")
    return site_url, backend_url


def collect():
    site_url, backend_url = urls()
    products = []
    for product in feed_products().iterator(chunk_size=CHUNK):
        data = product_data(product, site_url, backend_url)
        if data:
            products.append(data)
    return products, site_url


def write_atomically(name, writer, products, site_url):
    """The file is replaced in one step: a request never gets a half-written feed."""
    directory = os.path.join(settings.MEDIA_ROOT, FEEDS_DIR)
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=f".{name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            count = writer(out, products, site_url)
        os.chmod(tmp, 0o644)
        os.replace(tmp, os.path.join(directory, name))
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    return count


def build_feeds():
    """Rebuilds both feeds. Returns {file name: products written}."""
    products, site_url = collect()
    result = {
        GOOGLE_FILE: write_atomically(GOOGLE_FILE, write_google, products, site_url),
        YANDEX_FILE: write_atomically(YANDEX_FILE, write_yandex, products, site_url),
    }
    logger.info("Merchant feeds built: %s", result)
    return result
