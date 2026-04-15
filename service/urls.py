from django.urls import path
from .views import (
    ProductViewSet,
    BrandViewSet,
    SaleViewSet,
    AddsBrandsViewSet,
    CommentViewSet,
    FavouriteViewSet,
    CartViewSet,
    QuestionsViewSet,
    OrderViewSet,
    ServiceViewSet,
    MainPageViewSet,
)

urlpatterns = [
    path(
        "categories/",
        ProductViewSet.as_view({"get": "categories_list"}),
        name="categories_list",
    ),
    path(
        "categories/<int:pk>/",
        ProductViewSet.as_view({"get": "sub_category_list"}),
        name="sub_categories_list",
    ),
    path(
        "sub/categories/<int:pk>/",
        ProductViewSet.as_view({"get": "item_category_list"}),
        name="item_categories_list",
    ),
    path(
        "item/categories/<int:pk>/",
        ProductViewSet.as_view({"get": "item_category_detail"}),
        name="item_category_detail",
    ),
    path(
        "products/<int:pk>/",
        ProductViewSet.as_view({"get": "product_detail"}),
        name="products_detail",
    ),
    path("brands/", BrandViewSet.as_view({"get": "brand_list"}), name="brand_list"),
    path(
        "brands/<int:pk>/",
        BrandViewSet.as_view({"get": "brand_detail"}),
        name="brand_detail",
    ),
    path("sales/", SaleViewSet.as_view({"get": "sale_list"}), name="sale_list"),
    path("sales/main/", SaleViewSet.as_view({"get": "sale_main"}), name="sale_main"),
    path(
        "sales/<int:pk>/",
        SaleViewSet.as_view({"get": "sale_detail"}),
        name="sale_detail",
    ),
    path(
        "adds/brands/",
        AddsBrandsViewSet.as_view({"get": "adds_brands"}),
        name="adds_brands",
    ),
    path(
        "adds/brands/<int:pk>/",
        AddsBrandsViewSet.as_view({"get": "adds_brands_detail"}),
        name="adds_brands_detail",
    ),
    path(
        "search/",
        ProductViewSet.as_view({"get": "search_by_name"}),
        name="search_by_name",
    ),
    path(
        "product/filter/",
        ProductViewSet.as_view({"post": "product_filter"}),
        name="product_filter",
    ),
    path(
        "comments/",
        CommentViewSet.as_view({"post": "comment_create"}),
        name="comment_create",
    ),
    path(
        "comments/list/",
        CommentViewSet.as_view({"get": "product_comments"}),
        name="comments_list",
    ),
    path(
        "comments/<int:pk>/",
        CommentViewSet.as_view({"patch": "comment_update", "delete": "comment_delete"}),
        name="comment_action",
    ),
    path(
        "comments/me/",
        CommentViewSet.as_view({"get": "my_comments"}),
        name="my_comments",
    ),
    path("most/sold/", ProductViewSet.as_view({"get": "most_sold"}), name="most_sold"),
    path(
        "favourites/",
        FavouriteViewSet.as_view({"get": "favourite_list", "post": "create_favourite"}),
        name="favourite_action",
    ),
    path("cart/", CartViewSet.as_view({"get": "get_cart"}), name="get_cart"),
    path(
        "cart/item/",
        CartViewSet.as_view({"post": "create_cart_item", "patch": "update_cart_item"}),
        name="create_cart_item",
    ),
    path(
        "cart/item/bulk/",
        CartViewSet.as_view({"post": "cart_bulk_update"}),
        name="cart_bulk_update",
    ),
    path(
        "questions/",
        QuestionsViewSet.as_view({"post": "question_create"}),
        name="question_create",
    ),
    path(
        "questions/list/",
        QuestionsViewSet.as_view({"get": "questions_list"}),
        name="question_list",
    ),
    path(
        "questions/<int:pk>/",
        QuestionsViewSet.as_view(
            {"patch": "update_question", "delete": "delete_question"}
        ),
        name="create_question",
    ),
    path(
        "questions/me/",
        QuestionsViewSet.as_view({"get": "my_questions"}),
        name="my_questions",
    ),
    path(
        "recently/viewed/",
        ProductViewSet.as_view({"get": "recently_viewed"}),
        name="recently_viewed_products",
    ),
    path("order/", OrderViewSet.as_view({"post": "create_order"}), name="create_order"),
    path(
        "order/history/",
        OrderViewSet.as_view({"get": "orders_history_list"}),
        name="orders_history",
    ),
    path(
        "order/active/",
        OrderViewSet.as_view({"get": "orders_active_list"}),
        name="orders_active",
    ),
    path(
        "order/<int:pk>/",
        OrderViewSet.as_view({"get": "order_detail"}),
        name="order_detail",
    ),
    path(
        "services/",
        ServiceViewSet.as_view({"get": "service_list"}),
        name="services_list",
    ),
    path(
        "services/<int:pk>/",
        ServiceViewSet.as_view({"get": "service_detail"}),
        name="service_detail",
    ),
    path(
        "main/", MainPageViewSet.as_view({"get": "homepage_data"}), name="homepage_data"
    ),
    path(
        "most/search/",
        ProductViewSet.as_view({"get": "most_search"}),
        name="most_search",
    ),
    path(
        "comment/reply/<int:pk>/",
        CommentViewSet.as_view({"patch": "reply_update", "delete": "reply_delete"}),
        name="reply_action",
    ),
    path(
        "comment/<int:pk>/reply/",
        CommentViewSet.as_view({"post": "reply_create"}),
        name="reply_create",
    ),
    path(
        "comment/<int:pk>/replies/",
        CommentViewSet.as_view({"get": "reply_list"}),
        name="reply_list",
    ),
    path(
        "questions/<int:pk>/replies/",
        QuestionsViewSet.as_view({"get": "reply_list"}),
        name="question_reply_list",
    ),
    path(
        "questions/<int:pk>/reply/",
        QuestionsViewSet.as_view({"post": "reply_create"}),
        name="question_reply_create",
    ),
    path(
        "questions/reply/<int:pk>/",
        QuestionsViewSet.as_view({"patch": "reply_update", "delete": "reply_delete"}),
        name="question_reply_action",
    ),
    path(
        "order/<int:pk>/cancel/",
        OrderViewSet.as_view({"post": "cancel_order"}),
        name="order_cancel",
    ),
    path("order/pay/", OrderViewSet.as_view({"post": "order_pay"}), name="order_pay"),
    path(
        "characteristics/",
        ProductViewSet.as_view({"post": "product_characteristics"}),
        name="product_characteristics",
    ),
    path(
        "item-category/<int:pk>/attributes/",
        ProductViewSet.as_view({"get": "category_attributes"}),
        name="category_attributes",
    ),
    path(
        "sub-categories/create/",
        ProductViewSet.as_view(
            {"post": "sub_categories_create"}, name="sub_categories_create"
        ),
    ),
    path(
        "item-categories/create/",
        ProductViewSet.as_view(
            {"post": "item_categories_create"}, name="item_categories_create"
        ),
    ),
    path(
        "products/create/",
        ProductViewSet.as_view({"post": "product_create"}, name="product_create"),
    ),
]
