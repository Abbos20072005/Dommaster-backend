from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from .models import Comment, CartItem, Questions, Order, Product
from exceptions.error_exception import CustomApiException
from exceptions.error_messages import ErrorCodes
from .utils import send_telegram_message


@receiver(pre_save, sender=Order)
def decrease_product_quantity_on_collecting(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        previous = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    if previous.status != 1 and instance.status == 1:
        items = instance.order_items.select_related('product').all()
        products_to_update = []
        for item in items:
            product = item.product
            if product.quantity < item.quantity:
                raise CustomApiException(error_code=ErrorCodes.PRODUCT_QUANTITY_NOT_ENOUGH)
            product.quantity -= item.quantity
            products_to_update.append(product)
        if products_to_update:
            Product.objects.bulk_update(products_to_update, ['quantity'])
        send_telegram_message(instance)

    elif previous.status != 4 and instance.status == 4:
        items = instance.order_items.select_related('product').all()
        products_to_update = []
        for item in items:
            product = item.product
            product.quantity += item.quantity
            products_to_update.append(product)
        if products_to_update:
            Product.objects.bulk_update(products_to_update, ['quantity'])


@receiver(signal=[post_save, post_delete], sender=Comment)
def update_product_rating(sender, instance, **kwargs):
    instance.product.update_rating()


@receiver(signal=[post_save, post_delete], sender=CartItem)
def update_cart_total_price(sender, instance, **kwargs):
    cart = instance.cart
    cart.calculate_total_price()
    cart.save(update_fields=["total_price", "saved_price", "products_total_price"])


@receiver(signal=[post_save, post_delete], sender=Questions)
def update_questions_quantity(sender, instance, **kwargs):
    instance.product.update_questions()
