from django.utils.deprecation import MiddlewareMixin
from django.urls import reverse_lazy
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
        allowed_urls = (
            '/swagger/',
            reverse_lazy("login"),
            reverse_lazy("register"),
            reverse_lazy("otp_verify"),
            reverse_lazy("otp_resend"),
            reverse_lazy("banner_list"),
            reverse_lazy("chat_message_list"),
            reverse_lazy("about_us"),
            reverse_lazy("news_list"),
            reverse_lazy("news_detail"),
            reverse_lazy("articles_list"),
            reverse_lazy("articles_detail"),
            reverse_lazy("reviews_list"),
            reverse_lazy("reviews_detail"),
            reverse_lazy("video_list"),
            reverse_lazy("video_detail"),
            reverse_lazy("categories_list"),
            reverse_lazy("sub_categories_list"),
            reverse_lazy("item_categories_list"),
            reverse_lazy("item_category_detail"),
            reverse_lazy("products_detail"),
            reverse_lazy("brand_list"),
            reverse_lazy("brand_detail"),
            reverse_lazy("sale_products"),
            reverse_lazy("adds_brands"),
            reverse_lazy("adds_brands_detail"),
            reverse_lazy("search_by_name"),
            reverse_lazy("product_filter"),
            reverse_lazy("comments_list"),
            reverse_lazy("most_sold"),
            reverse_lazy("create_favourite"),
            reverse_lazy("favourite_action"),
            reverse_lazy("get_cart"),
            reverse_lazy("create_cart_item"),
            reverse_lazy("cart_bulk_update"),
            reverse_lazy("question_list")
        )
        return request.path in allowed_urls or request.path.startswith('/admin/')
