from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from abstract_model.base_model import BaseModel
from apps.authorization.models import Customer


class Project(BaseModel):
    """PRO customer's project (a site / object): order items are linked to it to count the expenses.
    Kept when the customer loses PRO - only hidden from the client API (`/pro/` answers 403)."""
    ACTIVE, ARCHIVED = "active", "archived"
    STATUS_CHOICES = (
        (ACTIVE, "Активный"),
        (ARCHIVED, "В архиве"),
    )
    NAME_MIN_LENGTH, NAME_MAX_LENGTH = 3, 100

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="pro_projects",
                                 verbose_name="Клиент")
    name = models.CharField(max_length=NAME_MAX_LENGTH, verbose_name="Название")
    address = models.CharField(max_length=255, blank=True, default="", verbose_name="Адрес")
    comment = models.TextField(blank=True, default="", verbose_name="Комментарий")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=ACTIVE, db_index=True,
                              verbose_name="Статус")
    archived_at = models.DateTimeField(blank=True, null=True, verbose_name="Архивирован")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Проект PRO"
        verbose_name_plural = "Проекты PRO"
        ordering = ("-created_at", "-id")
        constraints = [
            # two active projects of one customer can't share a name (case-insensitive)
            models.UniqueConstraint(Lower("name"), "customer", condition=Q(status="active"),
                                    name="uniq_active_project_name"),
        ]


class OrderItemProjectChange(BaseModel):
    """History of linking order items to projects (link / move / unlink)."""
    LINK, MOVE, UNLINK = "link", "move", "unlink"
    ACTION_CHOICES = (
        (LINK, "Привязка"),
        (MOVE, "Перенос"),
        (UNLINK, "Отвязка"),
    )

    # the order stays in the row when the item itself is replaced (admin order edit)
    order = models.ForeignKey("service.Order", on_delete=models.CASCADE, related_name="project_changes",
                              verbose_name="Заказ")
    order_item = models.ForeignKey("service.OrderItem", on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name="project_changes", verbose_name="Позиция заказа")
    action = models.CharField(max_length=10, choices=ACTION_CHOICES, verbose_name="Действие")
    old_project = models.ForeignKey(Project, on_delete=models.SET_NULL, blank=True, null=True, related_name="+",
                                    verbose_name="Был проект")
    new_project = models.ForeignKey(Project, on_delete=models.SET_NULL, blank=True, null=True, related_name="+",
                                    verbose_name="Новый проект")
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, blank=True, null=True, related_name="+",
                                 verbose_name="Клиент")

    def __str__(self):
        return f"{self.order_item_id}: {self.action}"

    class Meta:
        verbose_name = "Привязка позиции к проекту"
        verbose_name_plural = "История привязки позиций к проектам"
        ordering = ("-created_at", "-id")
