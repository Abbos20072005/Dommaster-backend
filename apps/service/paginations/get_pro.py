from django.core.paginator import Paginator


def get_pro_paginator(items, page, page_size, serializer_class, context):
    """Spring-style page of `items` (a queryset or a list) for the PRO endpoints."""
    paginator = Paginator(items, page_size)
    items_page = paginator.get_page(page)
    total_count = paginator.count
    return {
        "totalElements": total_count,
        "totalPages": paginator.num_pages,
        "size": page_size,
        "number": items_page.number,
        "numberOfElements": len(items_page),
        "first": not items_page.has_previous(),
        "last": not items_page.has_next(),
        "empty": total_count == 0,
        "content": serializer_class(items_page, many=True, context=context).data,
    }
