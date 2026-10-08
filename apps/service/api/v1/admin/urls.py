from django.urls import path
from rest_framework.routers import SimpleRouter
from .views import BrandViewSet, PartnerBrandViewSet, ProductBadgeViewSet, ProductCategoryViewSet, \
    ProductSubCategoryViewSet, ProductItemCategoryViewSet, ProductAttributeViewSet, OrderViewSet, ProductViewSet, \
    CommentViewSet, QuestionViewSet, CommentReplyViewSet, QuestionReplyViewSet, DashboardAPIView, ManagerViewSet, \
    OrderCommentViewSet, ProductModelViewSet, AddsBrandsViewSet, TodayAPIView, SaleViewSet, SalesAnalyticsAPIView

# SimpleRouter: mounted at the admin root, DefaultRouter's API-root view would take `api/v1/admin/`
router = SimpleRouter()
router.register("orders", OrderViewSet, basename="admin_order")
router.register("order-comments", OrderCommentViewSet, basename="admin_order_comment")
router.register("managers", ManagerViewSet, basename="admin_manager")
router.register("products", ProductViewSet, basename="admin_product")
router.register("brands", BrandViewSet, basename="admin_brand")
router.register("partner-brands", PartnerBrandViewSet, basename="admin_partner_brand")
router.register("adds-brands", AddsBrandsViewSet, basename="admin_adds_brands")
router.register("product-models", ProductModelViewSet, basename="admin_product_model")
router.register("product-badges",ProductBadgeViewSet, basename="admin_product_badge")
router.register("categories", ProductCategoryViewSet, basename="admin_category")
router.register("sub-categories", ProductSubCategoryViewSet, basename="admin_sub_category")
router.register("item-categories", ProductItemCategoryViewSet, basename="admin_item_category")
router.register("attributes", ProductAttributeViewSet, basename="admin_attribute")
router.register("comments", CommentViewSet, basename="admin_comment")
router.register("comment-replies", CommentReplyViewSet, basename="admin_comment_reply")
router.register("questions", QuestionViewSet, basename="admin_question")
router.register("question-replies", QuestionReplyViewSet, basename="admin_question_reply")

router.register("sales", SaleViewSet, basename="admin_sale")

urlpatterns = router.urls + [
    path("dashboard/", DashboardAPIView.as_view(), name="admin_dashboard"),
    path("today/", TodayAPIView.as_view(), name="admin_today"),
    path("analytics/sales/", SalesAnalyticsAPIView.as_view(), name="admin_analytics_sales"),
]
