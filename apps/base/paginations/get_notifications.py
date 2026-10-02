from apps.base.api.v1.client.serializers import NotificationSerializer
from django.core.paginator import Paginator


def get_notifications_paginator(context: dict, response_data, page: int, page_size: int):
    paginator = Paginator(response_data, page_size)
    notifications_page = paginator.get_page(page)
    total_count = paginator.count

    responses = {
        "totalElements": total_count,
        "totalPages": paginator.num_pages,
        "size": page_size,
        "number": page,
        "numberOfElements": len(notifications_page),
        "first": not notifications_page.has_previous(),
        "last": not notifications_page.has_next(),
        "empty": total_count == 0,
        "content": NotificationSerializer(notifications_page, many=True, context=context).data,
    }
    return responses
