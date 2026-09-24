from base.serializers import ArticlesSerializer
from django.core.paginator import Paginator
from django.db.models import Count

def get_articles_paginator(context: dict, response_data ,page: int, page_size: int):
    total_count = response_data.aggregate(total_count=Count('id'))['total_count']
    paginator = Paginator(response_data, page_size)
    articles_page = paginator.get_page(page)

    responses = {
        "totalElements": total_count,
        "totalPages": paginator.num_pages,
        "size": page_size,
        "number": page,
        "numberOfElements": len(articles_page),
        "first": not articles_page.has_previous(),
        "last": not articles_page.has_next(),
        "empty": total_count == 0,
        "content": ArticlesSerializer(articles_page, many=True, context=context).data,
    }
    return responses