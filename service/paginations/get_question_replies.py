from service.serializers import QuestionsReplySerializer
from django.core.paginator import Paginator

def get_question_replies_paginator(context: dict, response_data ,page: int, page_size: int):
    paginator = Paginator(response_data, page_size)
    question_replies_page = paginator.get_page(page)
    total_count = paginator.count

    responses = {
        "totalElements": total_count,
        "totalPages": paginator.num_pages,
        "size": page_size,
        "number": page,
        "numberOfElements": len(question_replies_page),
        "first": not question_replies_page.has_previous(),
        "last": not question_replies_page.has_next(),
        "empty": total_count == 0,
        "content": QuestionsReplySerializer(question_replies_page, many=True, context=context).data,
    }
    return responses