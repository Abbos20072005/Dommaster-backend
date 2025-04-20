from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Comment

@receiver(signal=[post_save, post_delete], sender=Comment)
def update_product_rating(sender, instance, **kwargs):
    instance.product.update_rating()
