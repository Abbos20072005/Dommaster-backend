from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from abstract_model.base_model import BaseModel
from .product import Product


class ProductModeration(BaseModel):
    """One submission of a product for publishing (`publish_status=review`) and its review.
    A pending row = the product is in the moderation queue; a product has at most one pending row."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    STATUS_CHOICES = (
        (PENDING, "В очереди"),
        (APPROVED, "Одобрен"),
        (REJECTED, "Возвращён"),
    )

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="moderations",
                                verbose_name="Продукт")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=PENDING, verbose_name="Статус")
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True,
                                     related_name="submitted_moderations", verbose_name="Отправил")
    submitted_at = models.DateTimeField(default=timezone.now, verbose_name="Отправлен")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True,
                                    related_name="reviewed_moderations", verbose_name="Проверил")
    reviewed_at = models.DateTimeField(blank=True, null=True, verbose_name="Проверен")
    # why it was returned (rejected only)
    reason = models.TextField(blank=True, default="", verbose_name="Причина возврата")

    def __str__(self):
        return f"{self.product} — {self.get_status_display()}"

    class Meta:
        verbose_name = "Модерация продукта"
        verbose_name_plural = "Модерация продуктов"
        ordering = ("-submitted_at", "-id")
        constraints = [
            models.UniqueConstraint(fields=["product"], condition=Q(status="pending"),
                                    name="unique_pending_product_moderation"),
        ]
        indexes = [
            models.Index(fields=["status", "submitted_at"], name="idx_moderation_status_submit"),
            models.Index(fields=["status", "reviewed_at"], name="idx_moderation_status_review"),
        ]
