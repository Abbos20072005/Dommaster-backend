from django.shortcuts import get_object_or_404
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.payment.atmos_refund import charge_transaction, charged_lines, remaining_lines
from apps.payment.models import AtmosRefund
from apps.service.models import Order
from apps.service.models.choices import PAYMENT_PAID
from utils.admin_views import AdminViewMixin
from ..serializers import OrderRefundSerializer, OrderRefundableSerializer


class OrderRefundViewSet(AdminViewMixin, mixins.ListModelMixin, mixins.CreateModelMixin, GenericViewSet):
    """Refunds of an order's Atmos card payment (BLD-545): `orders/<id>/refunds/` list / create,
    `refunds/available/` = the receipt lines that can still be refunded."""
    serializer_class = OrderRefundSerializer
    filter_backends = []

    def get_order(self):
        if not hasattr(self, "_order"):
            self._order = get_object_or_404(Order, pk=self.kwargs["order_id"])
        return self._order

    def get_queryset(self):
        return AtmosRefund.objects.filter(order=self.get_order()).select_related("created_by")

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "order": self.get_order()}

    @action(detail=False, methods=["get"], serializer_class=OrderRefundableSerializer)
    def available(self, request, order_id=None):
        order = self.get_order()
        charge = charge_transaction(order)
        lines = charged_lines(order, charge) if charge else None
        left = remaining_lines(order, charge) if lines is not None else None
        reason = ""
        if charge is None:
            reason = "Заказ не оплачен картой через Atmos"
        elif order.payment_status != PAYMENT_PAID:
            reason = "Оплата заказа не в статусе «Оплачен»"
        elif lines is None:
            reason = "Оплата прошла без строк чека (у позиции не было ИКПУ)"
        elif not left:
            reason = "Всё уже возвращено"
        charged = sum(line["amount"] for line in lines) if lines else None
        data = {"order": order.id, "payment_status": order.payment_status, "can_refund": not reason,
                "reason": reason, "charged_amount": charged,
                "refunded_amount": (charged - sum(line["amount"] for line in left)) if lines else 0,
                "lines": left or []}
        return Response(OrderRefundableSerializer(data).data)
