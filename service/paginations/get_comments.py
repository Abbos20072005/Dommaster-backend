from service.serializers import CommentSerializer
from django.core.paginator import Paginator
from django.db.models import Count
from service.models import Comment
from django.db.models import Q

def get_comments_paginator(context: dict, response_data, page: int, page_size: int):
    total_count = response_data.get("comments").aggregate(total_count=Count('id'))['total_count']
    paginator = Paginator(response_data.get("comments"), page_size)
    comments_page = paginator.get_page(page)

    products_comments = Comment.objects.filter(
        product_id=response_data.get("product_id")).aggregate(
        one=Count('id', filter=Q(product_rating=1)),
        two=Count('id', filter=Q(product_rating=2)),
        three=Count('id', filter=Q(product_rating=3)),
        four=Count('id', filter=Q(product_rating=4)),
        five=Count('id', filter=Q(product_rating=5)))

    responses = {
        "totalElements": total_count,
        "totalPages": paginator.num_pages,
        "size": page_size,
        "number": page,
        "numberOfElements": len(comments_page),
        "first": not comments_page.has_previous(),
        "last": not comments_page.has_next(),
        "empty": total_count == 0,
        "comment_ratings": {"5": products_comments["five"], "4": products_comments["four"],
                                            "3": products_comments["three"],
                                            "2": products_comments["two"],
                                            "1": products_comments["one"]},
        "content": CommentSerializer(comments_page, many=True, context=context).data,
    }
    return responses