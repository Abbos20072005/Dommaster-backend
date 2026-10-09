from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from .models import Comment, CartItem, Questions, Order, Product, ProductAttribute, ProductAttributeOption, \
    ProductAttributeValue, ProductItemCategoryAttribute
from exceptions.error_exception import CustomApiException
from exceptions.error_messages import ErrorCodes
from .models.choices import ORDER_EVENT_CANCELED, ORDER_EVENT_REFUNDED
from .outbox import emit_order_event
from .order_push import notify_order_status
from .product_filters import clear_category_filter_cache


# Order.save() is atomic, so stock changes and outbox events here commit together with the order
@receiver(pre_save, sender=Order)
def decrease_product_quantity_on_collecting(sender, instance, update_fields=None, **kwargs):
    instance._status_changed_to = None
    if not instance.pk:
        return

    try:
        previous = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    # picked up by push_order_status_to_customer once the order is saved
    if previous.status != instance.status and (update_fields is None or "status" in update_fields):
        instance._status_changed_to = instance.status

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

    elif previous.status != 4 and instance.status == 4:
        items = instance.order_items.select_related('product').all()
        products_to_update = []
        for item in items:
            product = item.product
            product.quantity += item.quantity
            products_to_update.append(product)
        if products_to_update:
            Product.objects.bulk_update(products_to_update, ['quantity'])
        emit_order_event(instance, ORDER_EVENT_CANCELED)

    # payment_status -> 3 is set only after Atmos confirmed cancel_hold, i.e. the money went back to the customer
    if previous.payment_status in (1, 2) and instance.payment_status == 3:
        emit_order_event(instance, ORDER_EVENT_REFUNDED, payload={
            "provider": "Atmos",
            "transaction_id": instance.hold_id,
            "amount": instance.total_price,
        })


@receiver(post_save, sender=Order)
def push_order_status_to_customer(sender, instance, **kwargs):
    status = getattr(instance, "_status_changed_to", None)
    if status is None:
        return
    instance._status_changed_to = None
    notify_order_status(instance.pk, instance.customer_id, status)


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


# Client filters are cached per item category; rows written with bulk_create / update() send no signals,
# that code calls clear_category_filter_cache() itself
@receiver(signal=[post_save, post_delete], sender=Product)
def invalidate_filter_cache_on_product_change(sender, instance, **kwargs):
    clear_category_filter_cache(instance.product_item_category_id)


@receiver(signal=[post_save, post_delete], sender=ProductAttributeValue)
def invalidate_filter_cache_on_value_change(sender, instance, **kwargs):
    clear_category_filter_cache(*Product.objects.filter(pk=instance.product_id)
                                .values_list("product_item_category_id", flat=True))


@receiver(signal=[post_save, post_delete], sender=ProductItemCategoryAttribute)
def invalidate_filter_cache_on_category_attribute_change(sender, instance, **kwargs):
    clear_category_filter_cache(instance.item_category_id)


@receiver(signal=[post_save, post_delete], sender=ProductAttribute)
def invalidate_filter_cache_on_attribute_change(sender, instance, **kwargs):
    clear_category_filter_cache(*instance.category_links.values_list("item_category_id", flat=True))


@receiver(signal=[post_save, post_delete], sender=ProductAttributeOption)
def invalidate_filter_cache_on_option_change(sender, instance, **kwargs):
    # renaming an option renames the product values (the admin serializer does it with update())
    clear_category_filter_cache(*ProductItemCategoryAttribute.objects.filter(attribute_id=instance.attribute_id)
                                .values_list("item_category_id", flat=True))
