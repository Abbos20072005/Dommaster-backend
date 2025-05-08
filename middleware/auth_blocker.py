from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from utils.get_user_token import validate_token

class IsAuthenticatedMiddleware(MiddlewareMixin):
    def process_view(self, request, callback, callback_args, callback_kwargs):
        if self.is_blocked(request):
            payload = validate_token(request)
            if not payload:
                return JsonResponse(
                    data={'result': '', 'error': 'Unauthorized access', 'ok': False},
                    status=401
                )
        return None

    @staticmethod
    def is_blocked(request):
        blocked_view_names = {
            "auth_me",
            "change_password",
            "update_customer_info",
            "addresses_list",
            "address_update",
            "promocode_checker",
            "promocode_list",
            "comment_create",
            "comment_action",
            "my_comments",
            "question_create",
            "my_questions",
            "recently_viewed_products",
            "create_order",
            "orders_history",
            "orders_active",
        }

        match = request.resolver_match
        return match and match.view_name in blocked_view_names
