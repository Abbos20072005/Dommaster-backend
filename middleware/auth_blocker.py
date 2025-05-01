from django.utils.deprecation import MiddlewareMixin
from django.urls import reverse
from django.http import JsonResponse
from utils.get_user_token import validate_token

class IsAuthenticatedMiddleware(MiddlewareMixin):
    def process_view(self, request, callback, callback_args, callback_kwargs):
        if self.is_allowed(request):
            return None
        payload = validate_token(request)
        if not payload:
            return JsonResponse(
                data={'result': '', 'error': 'Unauthorized access', 'ok': False},
                status=401
            )
        return None

    @staticmethod
    def is_allowed(request):
        allowed_paths = (
            '/swagger/',
            reverse("login"),
            reverse("register"),
            reverse("otp_verify"),
            reverse("otp_resend"),
            reverse("chat_message_list"),
            reverse("about_us"),
            reverse("search_by_name"),
            reverse("product_filter"),
            reverse("comments_list"),
            reverse("most_sold"),
            reverse("favourite_action"),
            reverse("get_cart"),
            reverse("create_cart_item"),
            reverse("cart_bulk_update"),
            reverse("question_list")
        )
        allowed_prefixes = (
            '/swagger/',
            '/media/',
            '/static/',
            '/api/v1/base/news/',
            '/api/v1/base/banner/',
            '/api/v1/base/articles/',
            '/api/v1/base/reviews/',
            '/api/v1/base/video/',
            '/api/v1/categories/',
            '/api/v1/sub/categories/',
            '/api/v1/item/categories/',
            '/api/v1/products/',
            '/api/v1/brands/',
            '/api/v1/sales/',
            '/api/v1/adds/brands/',
            '/admin/',
        )

        return (
                request.path in allowed_paths or
                any(request.path.startswith(prefix) for prefix in allowed_prefixes)
        )