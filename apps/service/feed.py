"""Personal product feed (`products/recommended/`): who is asking, their interest profile, the candidates,
how they are mixed, paging and the impression log. No ML: item categories scored by what the viewer did."""
import hashlib
import logging
import math
import random
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta

from django.core.cache import cache
from django.db.models import CharField, Count, Exists, OuterRef, Q, Value
from django.db.models.functions import Cast, Concat, MD5, TruncWeek
from django.utils import timezone

from apps.service.models import CartItem, Favourites, FeedImpression, InterestEvent, OrderItem, Product, \
    ProductImage, ProductItemCategory, ProductVariantItem, RecentlyViewedProducts

logger = logging.getLogger(__name__)

ORDER_CANCELED = 4

# `rec_source` of a product in the response. "cross_sell" is reserved in the contract: there are no
# hand-linked products to take it from yet
PERSONAL, POPULAR, FALLBACK = "personal", "popular", "fallback"

# All numbers below are starting values: tune them on the impression log (FeedImpression).
# signal -> (weight, half-life in days)
SIGNALS = {
    "purchase": (1.0, 90),
    "cart": (0.5, 30),
    "favourite": (0.4, 30),
    "search": (0.3, 10),
    "view": (0.15, 14),
}
PURCHASE_DAYS = 365
EVENT_DAYS = 90
EVENT_LIMIT = 500
SEARCH_CATEGORIES = 3
# a search typed letter by letter is one search: a longer / shorter query within this time replaces the row
SEARCH_MERGE_SECONDS = 30

TOP_CATEGORIES = 5
# a profile this strong (= one purchase) gets the full personal share, a weaker one gets less
FULL_SIGNAL = 1.0
BLOCK = 10
PERSONAL_PER_BLOCK = 7
MIN_PERSONAL_PER_BLOCK = 2
# of the personal places: products of the sibling categories (same sub category) of the top ones
NEIGHBOUR_PER_BLOCK = 1
CATEGORY_POOL = 40
NEIGHBOUR_POOL = 10
# no more than this many products of one item category in a row
MAX_RUN = 2
# the mixed part of the feed; after it the rest of the catalog goes in the seeded random order
HEAD_SIZE = 300

POPULAR_DAYS = 180
POPULAR_HALF_LIFE = 45
POPULAR_LIMIT = 200
POPULAR_SHUFFLE = 20
POPULAR_CACHE_KEY = "feed:popularity"
POPULAR_CACHE_TIMEOUT = 3600

RECENT_PURCHASE_DAYS = 14
SNAPSHOT_CACHE_TIMEOUT = 3600


@dataclass(frozen=True)
class Viewer:
    """Who asks for the feed. Any part may be missing."""
    customer_id: int = None
    device_id: str = ""
    cart_token: str = None
    favourite_token: str = None

    @classmethod
    def of(cls, request):
        return cls(
            customer_id=getattr(request.user, "id", None),
            device_id=(request.META.get("HTTP_X_DEVICE_ID") or "").strip()[:300],
            cart_token=request.COOKIES.get("cart_token"),
            favourite_token=request.COOKIES.get("favourite_token"),
        )

    @property
    def identity(self):
        """What tells this viewer from the others; None = nothing does."""
        if self.customer_id:
            return f"c:{self.customer_id}"
        if self.device_id:
            return f"d:{self.device_id}"
        if self.cart_token:
            return f"t:{self.cart_token}"
        return None

    @property
    def key(self):
        return hashlib.sha1((self.identity or "anon").encode()).hexdigest()[:20]


def seeded_order(products, seed):
    """Random order fixed by `seed` (`order_by("?")` reshuffles on every request, so pages would repeat products)."""
    return products.annotate(
        _random_order=MD5(Concat(Cast("id", CharField()), Value(f":{seed}"), output_field=CharField()))
    ).order_by("_random_order")


def random_products(seed):
    """The feed without personalization (`products/`): active products in the seeded random order."""
    return seeded_order(Product.objects.filter(is_active=True), seed)


def feed_request_id(viewer, seed):
    """The same for all pages of one feed (viewer + seed), without storing anything."""
    return uuid.uuid5(uuid.NAMESPACE_URL, f"dommaster:feed:{viewer.key}:{seed}")


def feed_variant(viewer, page):
    """Which feed the viewer gets: `page` is the HomePage (the switch + the share of the control group)."""
    if not page.personal_feed_enabled:
        return FeedImpression.DISABLED
    if viewer.identity and page.personal_feed_holdout_percent:
        bucket = int(hashlib.sha1(f"holdout:{viewer.identity}".encode()).hexdigest(), 16) % 100
        if bucket < page.personal_feed_holdout_percent:
            return FeedImpression.HOLDOUT
    return FeedImpression.PERSONAL


# ---- signals ----

def _events_q(viewer):
    """Events of the viewer: the customer's own + what the device did before anybody logged in on it."""
    q = Q(pk__in=[])
    if viewer.customer_id:
        q |= Q(customer_id=viewer.customer_id)
    if viewer.device_id:
        q |= Q(device_id=viewer.device_id, customer__isnull=True)
    return q


def record_view(request, product_id):
    """A product card was opened. Never breaks the request it is called from."""
    try:
        viewer = Viewer.of(request)
        if viewer.customer_id or viewer.device_id:
            InterestEvent.objects.create(event_type=InterestEvent.VIEW, customer_id=viewer.customer_id,
                                         device_id=viewer.device_id, product_id=product_id)
    except Exception:
        logger.exception("feed: view event was not saved")


def record_search(request, query, item_category_ids, results_count):
    """A search was made: `item_category_ids` = the categories most of the found products are in.
    Never breaks the request it is called from."""
    try:
        viewer = Viewer.of(request)
        query = query.strip()[:255]
        if not query or not (viewer.customer_id or viewer.device_id):
            return
        values = {"query": query, "item_category_ids": [pk for pk in item_category_ids if pk][:SEARCH_CATEGORIES],
                  "results_count": results_count}
        cache_key = f"feed:search:{viewer.key}"
        previous = cache.get(cache_key)
        if previous and (query.lower().startswith(previous[1]) or previous[1].startswith(query.lower())):
            event_id = previous[0]
            InterestEvent.objects.filter(pk=event_id).update(**values)
        else:
            event_id = InterestEvent.objects.create(event_type=InterestEvent.SEARCH, customer_id=viewer.customer_id,
                                                    device_id=viewer.device_id, **values).id
        cache.set(cache_key, (event_id, query.lower()), timeout=SEARCH_MERGE_SECONDS)
    except Exception:
        logger.exception("feed: search event was not saved")


def _cart_items(viewer):
    if viewer.customer_id:
        return CartItem.objects.filter(cart__customer_id=viewer.customer_id)
    if viewer.cart_token:
        return CartItem.objects.filter(cart__cart_token=viewer.cart_token)
    return CartItem.objects.none()


def _favourites(viewer):
    if viewer.customer_id:
        return Favourites.objects.filter(customer_id=viewer.customer_id)
    if viewer.favourite_token:
        return Favourites.objects.filter(favourite_token=viewer.favourite_token)
    return Favourites.objects.none()


def interest_profile(viewer, now=None):
    """{item category id: score}: what the viewer bought, put into the cart, liked, searched for and viewed,
    each signal with its weight, fading with age."""
    now = now or timezone.now()
    scores = defaultdict(float)

    def add(signal, category_id, when, share=1.0):
        if category_id:
            weight, half_life = SIGNALS[signal]
            age_days = max((now - when).total_seconds(), 0) / 86400
            scores[category_id] += share * weight * 0.5 ** (age_days / half_life)

    category = "product__product_item_category_id"
    if viewer.customer_id:
        # once per order: the quantity tells the size of the job, not the interest
        purchases = OrderItem.objects.filter(
            order__customer_id=viewer.customer_id, order__created_at__gte=now - timedelta(days=PURCHASE_DAYS),
        ).exclude(order__status=ORDER_CANCELED).values_list("order_id", category, "order__created_at").distinct()
        for _, category_id, when in purchases:
            add("purchase", category_id, when)
    for category_id, when in _cart_items(viewer).values_list(category, "created_at"):
        add("cart", category_id, when)
    for category_id, when in _favourites(viewer).values_list(category, "created_at"):
        add("favourite", category_id, when)

    since = now - timedelta(days=EVENT_DAYS)
    events = InterestEvent.objects.filter(_events_q(viewer), created_at__gte=since).order_by("-created_at") \
        .values_list("event_type", "product_id", category, "item_category_ids", "created_at")[:EVENT_LIMIT]
    # a product counts once, by its latest view
    views = {}
    for event_type, product_id, category_id, category_ids, when in events:
        if event_type == InterestEvent.VIEW:
            views.setdefault(product_id, (category_id, when))
        else:
            for pk in category_ids:
                add("search", pk, when, share=1 / len(category_ids))
    if viewer.customer_id:
        # views from before the events were written (one row per product, the time of the first view)
        viewed = RecentlyViewedProducts.objects.filter(customer_id=viewer.customer_id, created_at__gte=since)
        for product_id, category_id, when in viewed.values_list("product_id", category, "created_at"):
            views.setdefault(product_id, (category_id, when))
    for category_id, when in views.values():
        add("view", category_id, when)
    return dict(scores)


def product_popularity():
    """{product id: score}: in how many orders of the last POPULAR_DAYS days the product is (orders, not units:
    one bulk order must not make a bestseller), newer weeks weigh more. Cached."""
    scores = cache.get(POPULAR_CACHE_KEY)
    if scores is None:
        now = timezone.now()
        rows = OrderItem.objects.filter(order__created_at__gte=now - timedelta(days=POPULAR_DAYS)) \
            .exclude(order__status=ORDER_CANCELED).annotate(week=TruncWeek("order__created_at")) \
            .values("product_id", "week").annotate(orders=Count("order_id", distinct=True)).order_by()
        scores = defaultdict(float)
        for row in rows:
            scores[row["product_id"]] += row["orders"] * 0.5 ** ((now - row["week"]).days / POPULAR_HALF_LIFE)
        scores = dict(scores)
        cache.set(POPULAR_CACHE_KEY, scores, timeout=POPULAR_CACHE_TIMEOUT)
    return scores


# ---- candidates and mixing ----

def eligible_products():
    """What the feed may show: active, with a price, a picture and stock."""
    return Product.objects.filter(is_active=True, price__gt=0, quantity__gt=0).filter(
        Exists(ProductImage.objects.filter(product_id=OuterRef("pk"))))


def excluded_product_ids(viewer, now):
    """Not shown to the viewer: in the cart now, or bought in the last RECENT_PURCHASE_DAYS days."""
    ids = set(_cart_items(viewer).values_list("product_id", flat=True))
    if viewer.customer_id:
        ids.update(OrderItem.objects.filter(
            order__customer_id=viewer.customer_id, order__created_at__gte=now - timedelta(days=RECENT_PURCHASE_DAYS),
        ).exclude(order__status=ORDER_CANCELED).values_list("product_id", flat=True))
    ids.discard(None)
    return ids


def block_pattern(personal, neighbour):
    """What each of the BLOCK places of the feed is filled from, the kinds spread evenly.
    7 personal with 1 neighbour: top top top popular top top popular top neighbour popular."""
    pattern, taken = [], 0
    for place in range(BLOCK):
        if math.ceil((place + 1) * personal / BLOCK) == math.ceil(place * personal / BLOCK):
            pattern.append("popular")
            continue
        is_neighbour = (taken + 1) * neighbour // personal > taken * neighbour // personal
        pattern.append("neighbour" if is_neighbour else "top")
        taken += 1
    return pattern


def _seed_rank(product_id, seed):
    return hashlib.md5(f"{product_id}:{seed}".encode()).hexdigest()


def build_snapshot(viewer, seed, now=None):
    """The feed of the viewer for `seed`: the mixed head (product id + source, in order), what is left out of the
    whole feed, and how many products follow the head. Built once and cached, so the pages of one seed neither
    repeat nor skip products while the viewer adds to the cart or the stock changes."""
    now = now or timezone.now()
    profile = interest_profile(viewer, now)
    excluded = excluded_product_ids(viewer, now)
    popularity = product_popularity()

    top = sorted(profile, key=lambda pk: (-profile[pk], pk))[:TOP_CATEGORIES]
    neighbours = []
    if top:
        sub_categories = ProductItemCategory.objects.filter(id__in=top).values("product_sub_category_id")
        neighbours = list(ProductItemCategory.objects.filter(
            product_sub_category_id__in=sub_categories, is_active=True,
        ).exclude(id__in=top).order_by("id").values_list("id", flat=True))
    popular_ids = sorted(popularity, key=lambda pk: (-popularity[pk], pk))[:POPULAR_LIMIT]

    category_of = dict(eligible_products().filter(
        Q(product_item_category_id__in=[*top, *neighbours]) | Q(id__in=popular_ids),
    ).exclude(id__in=excluded).values_list("id", "product_item_category_id"))
    # variants of one product (sizes, colours): the feed shows one of them
    group_of = dict(ProductVariantItem.objects.filter(product_id__in=category_of)
                    .values_list("product_id", "group_id"))
    by_category = defaultdict(list)
    for product_id, category_id in category_of.items():
        by_category[category_id].append(product_id)

    rng = random.Random(seed)

    def category_pool(category_id, size):
        """The most ordered products of the category (ties in the seed order), shuffled: a new seed, a new order."""
        pool = sorted(by_category.get(category_id, ()),
                      key=lambda pk: (-popularity.get(pk, 0), _seed_rank(pk, seed)))[:size]
        rng.shuffle(pool)
        return pool

    top_pools = {pk: category_pool(pk, CATEGORY_POOL) for pk in top}
    neighbour_pool = [pk for category_id in neighbours for pk in category_pool(category_id, NEIGHBOUR_POOL)]
    rng.shuffle(neighbour_pool)
    # roughly by popularity, but not the same products on top after every refresh
    popular_pool = [pk for pk in popular_ids if pk in category_of]
    for start in range(0, len(popular_pool), POPULAR_SHUFFLE):
        chunk = popular_pool[start:start + POPULAR_SHUFFLE]
        rng.shuffle(chunk)
        popular_pool[start:start + POPULAR_SHUFFLE] = chunk

    signal = sum(profile[pk] for pk in top)
    personal = 0
    if top:
        personal = min(PERSONAL_PER_BLOCK,
                       max(MIN_PERSONAL_PER_BLOCK, round(PERSONAL_PER_BLOCK * signal / FULL_SIGNAL)))
    pattern = block_pattern(personal, personal * NEIGHBOUR_PER_BLOCK // PERSONAL_PER_BLOCK)

    head, used, used_groups = [], set(), set()
    credit = dict.fromkeys(top, 0.0)

    def take(pool, blocked):
        """Pops the first product of the pool that may go next; products already shown are dropped on the way."""
        index = 0
        while index < len(pool):
            product_id = pool[index]
            group = group_of.get(product_id)
            if product_id in used or (group is not None and group in used_groups):
                del pool[index]
            elif blocked is not None and category_of[product_id] == blocked:
                index += 1
            else:
                del pool[index]
                used.add(product_id)
                if group is not None:
                    used_groups.add(group)
                return product_id
        return None

    def take_top(blocked):
        # the top categories take turns in proportion to their scores
        for category_id in top:
            credit[category_id] += profile[category_id] / signal
        for category_id in sorted(top, key=lambda pk: -credit[pk]):
            product_id = take(top_pools[category_id], blocked)
            if product_id:
                credit[category_id] -= 1
                return product_id, PERSONAL
        return None

    def take_neighbour(blocked):
        product_id = take(neighbour_pool, blocked)
        return (product_id, PERSONAL) if product_id else None

    def take_popular(blocked):
        product_id = take(popular_pool, blocked)
        return (product_id, POPULAR) if product_id else None

    # a kind that has run out gives its place to the next one
    takers = {
        "top": (take_top, take_neighbour, take_popular),
        "neighbour": (take_neighbour, take_top, take_popular),
        "popular": (take_popular, take_top, take_neighbour),
    }

    def pick(kind, blocked):
        for taker in takers[kind]:
            item = taker(blocked)
            if item:
                return item
        return None

    while len(head) < HEAD_SIZE:
        kind = pattern[len(head) % BLOCK]
        run = [category_of[pk] for pk, _ in head[-MAX_RUN:]]
        blocked = run[0] if len(run) == MAX_RUN and len(set(run)) == 1 else None
        # only products of the blocked category are left: better a longer run than an empty place
        item = pick(kind, blocked) or (blocked is not None and pick(kind, None))
        if not item:
            break
        head.append(item)

    head_ids = [pk for pk, _ in head]
    left_out = sorted(excluded)
    return {
        "head": head,
        "excluded": left_out,
        "tail_count": eligible_products().exclude(id__in=[*head_ids, *left_out]).count(),
        "personalized": any(source == PERSONAL for _, source in head),
    }


def snapshot(viewer, seed):
    cache_key = f"feed:snapshot:{viewer.key}:{seed}"
    data = cache.get(cache_key)
    if data is None:
        data = build_snapshot(viewer, seed)
        cache.set(cache_key, data, timeout=SNAPSHOT_CACHE_TIMEOUT)
    return data


def page_items(data, seed, page, page_size):
    """(products in the whole feed, [(product id, source)] of the page): the head first, then the rest of the
    eligible catalog in the seeded random order."""
    head = data["head"]
    start = (page - 1) * page_size
    end = start + page_size
    items = list(head[start:end])
    if end > len(head) and data["tail_count"]:
        tail = seeded_order(eligible_products().exclude(id__in=[*(pk for pk, _ in head), *data["excluded"]]), seed)
        offset = max(start - len(head), 0)
        items += [(pk, FALLBACK) for pk in tail.values_list("id", flat=True)[offset:offset + page_size - len(items)]]
    return len(head) + data["tail_count"], items


def log_impression(viewer, seed, variant, result):
    """One row per response. Never breaks the request."""
    try:
        FeedImpression.objects.create(
            feed_request_id=result["feed_request_id"], customer_id=viewer.customer_id, device_id=viewer.device_id,
            seed=seed, page=result["number"], page_size=result["size"], variant=variant,
            personalized=result["personalized"],
            items=[[item["id"], item["rec_source"]] for item in result["content"]],
        )
    except Exception:
        logger.exception("feed: impression was not saved")
