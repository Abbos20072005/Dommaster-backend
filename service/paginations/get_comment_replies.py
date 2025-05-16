from service.serializers import CommentReplySerializer
from django.core.paginator import Paginator
from django.db.models import Count

def get_comment_replies_paginator(context: dict, response_data ,page: int, page_size: int):
    total_count = response_data.aggregate(total_count=Count('id'))['total_count']
    paginator = Paginator(response_data, page_size)
    comment_replies_page = paginator.get_page(page)

    responses = {
        "totalElements": total_count,
        "totalPages": paginator.num_pages,
        "size": page_size,
        "number": page,
        "numberOfElements": len(comment_replies_page),
        "first": not comment_replies_page.has_previous(),
        "last": not comment_replies_page.has_next(),
        "empty": total_count == 0,
        "content": CommentReplySerializer(comment_replies_page, many=True, context=context).data,
    }
    return responses