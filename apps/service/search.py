"""Text search over product names and brands (pg_trgm).

Shared by the client `product/filter/` (`q`) and the AI assistant's `search_products` tool.
"""
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Q
from django.db.models.functions import Greatest

# a product is found when any of its names / brand names is at least this similar to the query
MIN_SIMILARITY = 0.155


def search_products(products, q):
    """`products` that match `q`, annotated with `similarity` (the best of the six names).

    Not ordered: the caller orders by `-similarity` plus its own tie-breaker.
    """
    return products.select_related("brand").annotate(
        sim_name=TrigramSimilarity("name", q),
        sim_name_uz=TrigramSimilarity("name_uz", q),
        sim_name_ru=TrigramSimilarity("name_ru", q),
        sim_brand_name=TrigramSimilarity("brand__name", q),
        sim_brand_uz=TrigramSimilarity("brand__name_uz", q),
        sim_brand_ru=TrigramSimilarity("brand__name_ru", q),
    ).annotate(
        similarity=Greatest(
            "sim_name", "sim_name_uz", "sim_name_ru",
            "sim_brand_name", "sim_brand_uz", "sim_brand_ru",
        )
    ).filter(
        Q(similarity__gt=MIN_SIMILARITY) |
        Q(name__icontains=q) | Q(name_uz__icontains=q) | Q(name_ru__icontains=q) |
        Q(brand__name__icontains=q) | Q(brand__name_uz__icontains=q) | Q(brand__name_ru__icontains=q)
    )
