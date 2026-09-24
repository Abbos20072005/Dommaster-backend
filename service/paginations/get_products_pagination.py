from service.serializers import ProductSerializer
from django.core.paginator import Paginator

def get_products_paginator(context: dict, response_data ,page: int, page_size: int):
    paginator = Paginator(response_data, page_size)
    products_page = paginator.get_page(page)
    total_count = paginator.count

    responses = {
        "totalElements": total_count,
        "totalPages": paginator.num_pages,
        "size": page_size,
        "number": page,
        "numberOfElements": len(products_page),
        "first": not products_page.has_previous(),
        "last": not products_page.has_next(),
        "empty": total_count == 0,
        "content": ProductSerializer(products_page, many=True, context=context).data,
    }
    return responses