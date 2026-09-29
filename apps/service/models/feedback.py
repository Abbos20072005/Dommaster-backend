from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from abstract_model.base_model import BaseModel
from apps.authorization.models import Customer
from .product import Product


class Comment(BaseModel):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, verbose_name="Клиент")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="product_comment",
                                verbose_name="Продукт")
    product_rating = models.IntegerField(default=0, validators=[MinValueValidator(1), MaxValueValidator(5)],
                                         verbose_name="Рейтинг продукта")
    comment = models.TextField(verbose_name="Коментарий")
    is_visible = models.BooleanField(default=True, verbose_name="Виден")

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Коментарий"
        verbose_name_plural = "Коментарии"
        indexes = [
            models.Index(fields=['product'], name='idx_comment_product'),
        ]


class CommentReply(BaseModel):
    comment = models.ForeignKey(Comment, related_name="comment_reply", on_delete=models.CASCADE,
                                verbose_name="Коментарий")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, blank=True, null=True, verbose_name="Клиент")
    reply_comment = models.TextField(verbose_name="Коментарий ответа")
    is_admin = models.BooleanField(default=False, verbose_name="Админ")
    is_visible = models.BooleanField(default=True, verbose_name="Виден")

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Ответ коментария"
        verbose_name_plural = "Ответы коментариям"
        ordering = ("-created_at",)


class CommentImages(BaseModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="Клиент")
    comment = models.ForeignKey(Comment, related_name="comment_image", on_delete=models.CASCADE,
                                verbose_name="Коментарий")
    image = models.ImageField(upload_to="comment/images/", verbose_name="Изображение")

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Изображение комментария"
        verbose_name_plural = "Изображения комментариев"
        ordering = ("-created_at",)


class Questions(BaseModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="customer_question",
                                 verbose_name="Клиент")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="product_question",
                                verbose_name="Продукт")
    question = models.TextField(verbose_name="Вопрос")
    is_visible = models.BooleanField(default=True, verbose_name="Виден")

    def __str__(self):
        return self.product.name

    class Meta:
        verbose_name = "Вопрос"
        verbose_name_plural = "Вопросы"


class QuestionsReply(BaseModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, blank=True, null=True, verbose_name="Клиент")
    question = models.ForeignKey(Questions, related_name="question_reply", on_delete=models.CASCADE,
                                 verbose_name="Вопрос")
    answer = models.TextField(verbose_name="Ответ")
    is_admin = models.BooleanField(default=False, verbose_name="Админ")
    is_visible = models.BooleanField(default=False, verbose_name="Виден")

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Ответ вопросу"
        verbose_name_plural = "Ответы вопросам"
        ordering = ("-created_at",)
