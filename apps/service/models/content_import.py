from django.conf import settings
from django.db import models

from abstract_model.base_model import BaseModel
from .product import Product


class ContentImport(BaseModel):
    """One upload of the product content workbook (`apps/service/content_import.py`) — the batch of the audit
    log: who uploaded and applied it, the validation report and, in `changes`, every field it changed."""
    VALIDATING = "validating"
    READY = "ready"
    INVALID = "invalid"
    APPLYING = "applying"
    APPLIED = "applied"
    FAILED = "failed"
    STATUS_CHOICES = (
        (VALIDATING, "Проверяется"),
        (READY, "Готов к применению"),
        (INVALID, "Есть ошибки"),
        (APPLYING, "Применяется"),
        (APPLIED, "Применён"),
        (FAILED, "Не применён"),
    )

    file = models.FileField(upload_to="content_imports/", verbose_name="Файл")
    file_name = models.CharField(max_length=255, blank=True, default="", verbose_name="Имя файла")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=VALIDATING, verbose_name="Статус")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name="content_imports", verbose_name="Загрузил")
    applied_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name="applied_content_imports", verbose_name="Применил")
    applied_at = models.DateTimeField(blank=True, null=True, verbose_name="Применён")
    # the editable columns found in the file and the languages they cover
    columns = models.JSONField(default=list, blank=True, verbose_name="Колонки")
    languages = models.JSONField(default=list, blank=True, verbose_name="Языки")
    # 1C / read-only / unknown columns of the file — never applied
    ignored_columns = models.JSONField(default=list, blank=True, verbose_name="Пропущенные колонки")
    rows_total = models.PositiveIntegerField(default=0, verbose_name="Строк")
    rows_changed = models.PositiveIntegerField(default=0, verbose_name="Строк с изменениями")
    rows_unchanged = models.PositiveIntegerField(default=0, verbose_name="Строк без изменений")
    rows_error = models.PositiveIntegerField(default=0, verbose_name="Строк с ошибками")
    changes_count = models.PositiveIntegerField(default=0, verbose_name="Изменений")
    # [{"row", "product", "column", "message"}] (the first `content_import.MAX_ERRORS`)
    errors = models.JSONField(default=list, blank=True, verbose_name="Ошибки")
    # why the file could not be read or the apply failed
    error = models.TextField(blank=True, default="", verbose_name="Ошибка")

    def __str__(self):
        return f"{self.file_name or self.pk} — {self.get_status_display()}"

    class Meta:
        verbose_name = "Импорт контента"
        verbose_name_plural = "Импорты контента"
        ordering = ("-created_at", "-id")


class ContentImportChange(models.Model):
    """One field of one product an import changes (written by the validation, applied all at once)."""
    content_import = models.ForeignKey(ContentImport, on_delete=models.CASCADE, related_name="changes",
                                       verbose_name="Импорт")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, blank=True, null=True,
                                related_name="content_import_changes", verbose_name="Продукт")
    row = models.PositiveIntegerField(verbose_name="Строка файла")
    field = models.CharField(max_length=64, verbose_name="Поле")
    old_value = models.TextField(blank=True, default="", verbose_name="Было")
    new_value = models.TextField(blank=True, default="", verbose_name="Стало")

    def __str__(self):
        return f"{self.product_id}.{self.field}"

    class Meta:
        verbose_name = "Изменение импорта контента"
        verbose_name_plural = "Изменения импорта контента"
        ordering = ("row", "id")
