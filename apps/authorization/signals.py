from django.db import transaction
from django.db.models.signals import pre_save, post_delete
from django.dispatch import receiver

from apps.authorization.models import Customer


def delete_file_on_commit(storage, name):
    """Remove a stored file only after the DB change that dropped it is committed."""
    if name:
        transaction.on_commit(lambda: storage.delete(name))


@receiver(pre_save, sender=Customer)
def delete_replaced_avatar(sender, instance, update_fields=None, **kwargs):
    """Avatar replaced or cleared (client API, admin, anywhere) → old file is removed from storage."""
    if not instance.pk or (update_fields is not None and "avatar" not in update_fields):
        return
    old_name = Customer.objects.filter(pk=instance.pk).values_list("avatar", flat=True).first()
    if old_name and old_name != instance.avatar.name:
        delete_file_on_commit(instance.avatar.storage, old_name)


@receiver(post_delete, sender=Customer)
def delete_avatar_on_customer_delete(sender, instance, **kwargs):
    delete_file_on_commit(instance.avatar.storage, instance.avatar.name)
