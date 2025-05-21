from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from .models import Comment, CartItem, Questions, Order
from django.db.models import F
from exceptions.error_exception import CustomApiException
from exceptions.error_messages import ErrorCodes
from .utils import send_telegram_message


@receiver(pre_save, sender=Order)
def decrease_product_quantity_on_collecting(sender, instance, **kwargs):
    if not instance.pk:
        return

    previous = sender.objects.get(pk=instance.pk)
    if previous.status != 1 and instance.status == 1:
        for item in instance.order_items.all():
            product = item.product
            if product.quantity < item.quantity:
                raise CustomApiException(error_code=ErrorCodes.PRODUCT_QUANTITY_NOT_ENOUGH)
            product.quantity = F("quantity") - item.quantity
            product.save()
            product.refresh_from_db()
        send_telegram_message(instance)

    elif previous.status != 4 and instance.status == 4:
        for item in instance.order_items.all():
            product = item.product
            product.quantity = F("quantity") + item.quantity
            product.save()
            product.refresh_from_db()


@receiver(signal=[post_save, post_delete], sender=Comment)
def update_product_rating(sender, instance, **kwargs):
    instance.product.update_rating()


@receiver(signal=[post_save, post_delete], sender=CartItem)
def update_cart_total_price(sender, instance, **kwargs):
    cart = instance.cart
    cart.calculate_total_price()
    cart.save()


@receiver(signal=[post_save, post_delete], sender=Questions)
def update_questions_quantity(sender, instance, **kwargs):
    instance.product.update_questions()
