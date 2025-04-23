from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Comment, CartItem, Questions

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