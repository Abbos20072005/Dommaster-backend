from datetime import timedelta
from django.db import transaction
from django.db.models import Count, Exists, IntegerField, Max, OuterRef, Q, Subquery, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from apps.authorization.activity import record_admin
from apps.authorization.roles import RoleError, change_role
from apps.authorization.models import Customer, CustomerActivity, CustomerNote, CustomerRoleChange, FcmToken
from utils.admin_views import AdminModelViewSet
from ..filters import CustomerFilter, CustomerSearchFilter, NullsLastOrderingFilter, active_since
from ..serializers import CustomerSerializer, CustomerDetailSerializer, CustomerStatsSerializer, \
    RoleChangeSerializer, RoleHistorySerializer, RevealPhoneSerializer, CustomerNoteSerializer, \
    CustomerActivitySerializer

ORDER_COMPLETED = 3
ORDER_CANCELED = 4
ORDERED_DAYS = 30
Kind = CustomerActivity.Kind
# fields of an admin PATCH that go to the journal as "profile updated" (is_blocked has events of its own)
JOURNAL_FIELDS = ("full_name", "phone_number", "email", "verified", "segment", "tags", "language")


class CustomerViewSet(AdminModelViewSet):
    filterset_class = CustomerFilter
    filter_backends = [DjangoFilterBackend, CustomerSearchFilter, NullsLastOrderingFilter]
    search_fields = ("full_name", "phone_number", "email")
    ordering_fields = ("id", "full_name", "created_at", "last_login", "orders_count", "total_purchase",
                       "last_order_at")
    ordering = ("-created_at",)

    def get_queryset(self):
        devices = FcmToken.objects.filter(customer=OuterRef("pk")).order_by().values("customer") \
            .annotate(n=Count("device_id", distinct=True)).values("n")
        qs = Customer.objects.annotate(
            # only completed orders count as purchases
            orders_count=Count("order", filter=Q(order__status=ORDER_COMPLETED)),
            total_purchase=Coalesce(Sum("order__total_price", filter=Q(order__status=ORDER_COMPLETED)), 0.0),
            last_order_at=Max("order__created_at"),
            # there is no goods-return model yet: "returns" = canceled orders
            returns_count=Count("order", filter=Q(order__status=ORDER_CANCELED)),
            active_devices=Coalesce(Subquery(devices, output_field=IntegerField()), 0),
        )
        # the list shows deleted customers only when asked (?is_deleted=true = the "deleted" tab)
        if self.action == "list" and "is_deleted" not in self.request.query_params:
            qs = qs.filter(is_deleted=False)
        if self.action == "retrieve":
            qs = qs.prefetch_related("customeraddresses_set")
        return qs

    def get_serializer_class(self):
        return {
            "retrieve": CustomerDetailSerializer,
            "stats": CustomerStatsSerializer,
            "role": RoleChangeSerializer,
            "role_history": RoleHistorySerializer,
            "reveal_phone": RevealPhoneSerializer,
            "notes": CustomerNoteSerializer,
            "activity": CustomerActivitySerializer,
        }.get(self.action, CustomerSerializer)

    @transaction.atomic
    def perform_update(self, serializer):
        customer = serializer.instance
        before = {field: getattr(customer, field) for field in (*JOURNAL_FIELDS, "is_blocked")}
        serializer.save()
        changed = [field for field in JOURNAL_FIELDS if getattr(customer, field) != before[field]]
        if changed:
            record_admin(customer, Kind.UPDATED, self.request.user, fields=changed)
        if customer.is_blocked != before["is_blocked"]:
            record_admin(customer, Kind.BLOCKED if customer.is_blocked else Kind.UNBLOCKED, self.request.user)

    @transaction.atomic
    def perform_destroy(self, instance):
        """Soft delete: the row stays (orders, "deleted" tab), tokens and push tokens die."""
        if instance.is_deleted:
            return
        instance.soft_delete()
        record_admin(instance, Kind.DELETED, self.request.user)

    @action(detail=False, methods=["get"], filter_backends=[], pagination_class=None)
    def stats(self, request):
        ordered = Exists(self._orders_since(timezone.now() - timedelta(days=ORDERED_DAYS)))
        live = Q(is_deleted=False)
        data = Customer.objects.annotate(ordered=ordered).aggregate(
            total=Count("id", filter=live),
            active=Count("id", filter=live & Q(last_login__gte=active_since())),
            b2b=Count("id", filter=live & Q(role=Customer.Role.PRORAB)),
            blocked=Count("id", filter=live & Q(is_blocked=True)),
            ordered_30d=Count("id", filter=live & Q(ordered=True)),
            deleted=Count("id", filter=Q(is_deleted=True)),
        )
        return Response(self.get_serializer(data).data)

    @staticmethod
    def _orders_since(since):
        from apps.service.models import Order
        return Order.objects.filter(customer=OuterRef("pk"), created_at__gte=since)

    @action(detail=True, methods=["post"], url_path="role", filter_backends=[])
    def role(self, request, pk=None):
        """Grants / revokes PRO (role prorab / user); revoking needs `reason`. Projects are kept either way."""
        customer = self.get_object()
        serializer = self.get_serializer(data=request.data, context={"customer": customer})
        serializer.is_valid(raise_exception=True)
        try:
            change_role(customer.pk, serializer.validated_data["role"], request.user,
                        serializer.validated_data["reason"])
        except RoleError as e:  # changed by a concurrent request
            raise ValidationError({"role": str(e)})
        return Response(CustomerDetailSerializer(self.get_queryset().get(pk=customer.pk)).data)

    @action(detail=True, methods=["get"], url_path="role-history", filter_backends=[])
    def role_history(self, request, pk=None):
        customer = self.get_object()
        changes = CustomerRoleChange.objects.filter(customer=customer).select_related(
            "changed_by__staff_profile")
        page = self.paginate_queryset(changes)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)

    @action(detail=True, methods=["post"], url_path="reveal-phone", filter_backends=[])
    def reveal_phone(self, request, pk=None):
        """The full phone number (the list / detail show it masked); every call goes to the journal."""
        customer = self.get_object()
        record_admin(customer, Kind.PHONE_REVEALED, request.user)
        return Response(self.get_serializer({"phone_number": customer.phone_number}).data)

    @action(detail=True, methods=["post"], url_path="logout-all", filter_backends=[])
    def logout_all(self, request, pk=None):
        """Ends the customer's sessions on every device: tokens issued so far are refused, push tokens dropped."""
        customer = self.get_object()
        with transaction.atomic():
            customer.end_sessions()
            record_admin(customer, Kind.LOGGED_OUT_ALL, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get", "post"], url_path="notes", filter_backends=[])
    def notes(self, request, pk=None):
        """Internal staff notes, newest first; never shown to the customer."""
        customer = self.get_object()
        if request.method == "POST":
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(customer=customer, author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        notes = CustomerNote.objects.filter(customer=customer).select_related("author__staff_profile")
        page = self.paginate_queryset(notes)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)

    @action(detail=True, methods=["delete"], url_path=r"notes/(?P<note_id>\d+)", filter_backends=[])
    def delete_note(self, request, pk=None, note_id=None):
        """Only the author or a super admin deletes a note."""
        note = get_object_or_404(CustomerNote, pk=note_id, customer_id=self.get_object().pk)
        if note.author_id != request.user.id and not request.user.is_superuser:
            raise PermissionDenied("Only the author or a super admin can delete this note.")
        note.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path="activity", filter_backends=[])
    def activity(self, request, pk=None):
        """Customer journal, newest first (history starts at the deploy of the journal)."""
        customer = self.get_object()
        events = CustomerActivity.objects.filter(customer=customer).select_related("actor__staff_profile")
        page = self.paginate_queryset(events)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)
