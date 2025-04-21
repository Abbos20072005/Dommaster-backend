from base.serializers import QuestionsSerializer
from django.core.paginator import Paginator
from django.db.models import Count

def get_questions_paginator(context: dict, response_data ,page: int, page_size: int):
    total_count = response_data.aggregate(total_count=Count('id'))['total_count']
    paginator = Paginator(response_data, page_size)
    questions_page = paginator.get_page(page)

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