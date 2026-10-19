from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from apps.authorization.account_type import AccountTypeError, change_account_type
from apps.authorization.models import Customer, CustomerAccountTypeChange
from utils.admin_views import AdminModelViewSet
from ..filters import CustomerFilter, active_since
from ..serializers import CustomerSerializer, CustomerDetailSerializer, CustomerStatsSerializer,     AccountTypeChangeSerializer, AccountTypeHistorySerializer

ORDER_COMPLETED = 3


class CustomerViewSet(AdminModelViewSet):
    filterset_class = CustomerFilter
    search_fields = ("full_name", "phone_number", "email")
    ordering_fields = ("id", "full_name", "created_at", "last_login", "orders_count", "total_purchase")
    ordering = ("-created_at",)

    def get_queryset(self):
        qs = Customer.objects.annotate(
            # only completed orders count as purchases
            orders_count=Count("order", filter=Q(order__status=ORDER_COMPLETED)),
            total_purchase=Coalesce(Sum("order__total_price", filter=Q(order__status=ORDER_COMPLETED)), 0.0),
        )
        if self.action == "retrieve":
            qs = qs.prefetch_related("customeraddresses_set")
        return qs

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CustomerDetailSerializer
        if self.action == "stats":
            return CustomerStatsSerializer
        if self.action == "account_type":
            return AccountTypeChangeSerializer
        if self.action == "account_type_history":
            return AccountTypeHistorySerializer
        return CustomerSerializer

    @action(detail=False, methods=["get"], filter_backends=[], pagination_class=None)
    def stats(self, request):
        data = Customer.objects.aggregate(
            total=Count("id"),
            active=Count("id", filter=Q(last_login__gte=active_since())),
            b2b=Count("id", filter=Q(role=Customer.Role.PRORAB)),
            pro=Count("id", filter=Q(account_type=Customer.AccountType.PRO)),
            blocked=Count("id", filter=Q(is_blocked=True)),
        )
        return Response(self.get_serializer(data).data)

    @action(detail=True, methods=["post"], url_path="account-type", filter_backends=[])
    def account_type(self, request, pk=None):
        """Grants / revokes PRO; revoking needs `reason`. Projects of the customer are kept either way."""
        customer = self.get_object()
        serializer = self.get_serializer(data=request.data, context={"customer": customer})
        serializer.is_valid(raise_exception=True)
        try:
            change_account_type(customer.pk, serializer.validated_data["account_type"], request.user,
                                serializer.validated_data["reason"])
        except AccountTypeError as e:  # changed by a concurrent request
            raise ValidationError({"account_type": str(e)})
        return Response(CustomerDetailSerializer(self.get_queryset().get(pk=customer.pk)).data)

    @action(detail=True, methods=["get"], url_path="account-type-history", filter_backends=[])
    def account_type_history(self, request, pk=None):
        customer = self.get_object()
        changes = CustomerAccountTypeChange.objects.filter(customer=customer).select_related(
            "changed_by__staff_profile")
        page = self.paginate_queryset(changes)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)
