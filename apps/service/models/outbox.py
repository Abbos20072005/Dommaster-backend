import uuid

from django.db import models
from django.utils import timezone

from abstract_model.base_model import BaseModel
from .choices import ORDER_EVENT_TYPE, OUTBOX_STATUS, OUTBOX_PENDING
from .order import Order


class OrderOutboxEvent(BaseModel):
    """Transactional outbox: written in the same DB transaction as the order change, delivered after commit."""
    event_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, verbose_name="ID события")
    event_type = models.CharField(max_length=32, choices=ORDER_EVENT_TYPE, verbose_name="Тип события")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="outbox_events", verbose_name="Заказ")
    status = models.CharField(max_length=16, choices=OUTBOX_STATUS, default=OUTBOX_PENDING, verbose_name="Статус")
    attempts = models.PositiveIntegerField(default=0, verbose_name="Количество попыток")
    next_attempt_at = models.DateTimeField(default=timezone.now, verbose_name="Следующая попытка")
    payload = models.JSONField(default=dict, blank=True, verbose_name="Данные")
    last_error = models.TextField(blank=True, default="", verbose_name="Последняя ошибка")
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Отправлено")

    def __str__(self):
        return f"{self.event_type} #{self.order_id}"

    class Meta:
        verbose_name = "Событие заказа (outbox)"
        verbose_name_plural = "События заказов (outbox)"
        indexes = [
            models.Index(fields=["status", "next_attempt_at"], name="idx_outbox_status_next"),
        ]
