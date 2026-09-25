from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class AdminPagination(PageNumberPagination):
    """Admin (dashboard) lists: ?page=2&page_size=50"""
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        page = self.page
        return Response({
            "count": page.paginator.count,
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "next_page": page.next_page_number() if page.has_next() else None,
            "previous_page": page.previous_page_number() if page.has_previous() else None,
            "results": data,
        })

    def get_paginated_response_schema(self, schema):
        response_schema = super().get_paginated_response_schema(schema)
        response_schema["properties"]["next_page"] = {"type": "integer", "nullable": True, "example": 3}
        response_schema["properties"]["previous_page"] = {"type": "integer", "nullable": True, "example": 1}
        return response_schema
