from django.db import models

from abstract_model.base_model import BaseModel
from apps.authorization.models import Customer
from .choices import ORDER_CHANNEL


class AssistantConversation(BaseModel):
    # One conversation of the AI shopping assistant (Gemini). Logic: apps/service/assistant/
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="assistant_conversations", verbose_name="Клиент")
    # a visitor who is not logged in: the `X-Device-Id` header, else the `cart_token` cookie, else the IP
    session_id = models.CharField(max_length=300, blank=True, default="", verbose_name="ID сессии")
    language = models.CharField(max_length=2, default="ru", verbose_name="Язык")
    platform = models.CharField(max_length=10, choices=ORDER_CHANNEL, blank=True, default="",
                                verbose_name="Платформа")
    messages_count = models.PositiveIntegerField(default=0, verbose_name="Сообщений")
    input_tokens = models.PositiveIntegerField(default=0, verbose_name="Входные токены")
    output_tokens = models.PositiveIntegerField(default=0, verbose_name="Выходные токены")

    def __str__(self):
        return f"Диалог #{self.pk}"

    class Meta:
        verbose_name = "Диалог AI ассистента"
        verbose_name_plural = "Диалоги AI ассистента"
        indexes = [
            models.Index(fields=["created_at"], name="idx_assistconv_created"),
        ]


class AssistantMessage(BaseModel):
    USER, ASSISTANT = "user", "assistant"
    ROLE_CHOICES = ((USER, "Клиент"), (ASSISTANT, "Ассистент"))

    conversation = models.ForeignKey(AssistantConversation, on_delete=models.CASCADE, related_name="messages",
                                     verbose_name="Диалог")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, verbose_name="Роль")
    text = models.TextField(blank=True, default="", verbose_name="Текст")
    # the products shown as cards with this answer, in order (always ones a tool returned)
    product_ids = models.JSONField(default=list, blank=True, verbose_name="Товары")
    # the tools the model called for this answer: [{"name", "args", "count"}]
    tool_calls = models.JSONField(default=list, blank=True, verbose_name="Вызовы инструментов")
    input_tokens = models.PositiveIntegerField(default=0, verbose_name="Входные токены")
    output_tokens = models.PositiveIntegerField(default=0, verbose_name="Выходные токены")
    latency_ms = models.PositiveIntegerField(default=0, verbose_name="Время ответа, мс")
    # "" = answered; otherwise why the model gave no answer
    error = models.CharField(max_length=500, blank=True, default="", verbose_name="Ошибка")

    def __str__(self):
        return f"{self.role} #{self.pk}"

    class Meta:
        verbose_name = "Сообщение AI ассистента"
        verbose_name_plural = "Сообщения AI ассистента"
        ordering = ("id",)
