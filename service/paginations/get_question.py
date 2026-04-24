from service.serializers import QuestionsSerializer
from django.core.paginator import Paginator

def get_questions_paginator(context: dict, response_data ,page: int, page_size: int):
    paginator = Paginator(response_data, page_size)
    questions_page = paginator.get_page(page)
    total_count = paginator.count

    responses = {
        "totalElements": total_count,
        "totalPages": paginator.num_pages,
        "size": page_size,
        "number": page,
        "numberOfElements": len(questions_page),
        "first": not questions_page.has_previous(),
        "last": not questions_page.has_next(),
        "empty": total_count == 0,
        "content": QuestionsSerializer(questions_page, many=True, context=context).data,
    }
    return responses