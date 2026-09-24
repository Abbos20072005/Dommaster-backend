from base.serializers import NewsSerializer
from django.core.paginator import Paginator
from django.db.models import Count

def get_news_paginator(context: dict, response_data ,page: int, page_size: int):
    total_count = response_data.aggregate(total_count=Count('id'))['total_count']
    paginator = Paginator(response_data, page_size)
    news_page = paginator.get_page(page)

    responses = {
        "totalElements": total_count,
        "totalPages": paginator.num_pages,
        "size": page_size,
        "number": page,
        "numberOfElements": len(news_page),
        "first": not news_page.has_previous(),
        "last": not news_page.has_next(),
        "empty": total_count == 0,
        "content": NewsSerializer(news_page, many=True, context=context).data,
    }
    return responses