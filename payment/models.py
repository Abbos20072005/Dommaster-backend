from django.db import models
from django.conf import settings
from django.utils.module_loading import import_string

AccountModel = import_string(settings.CLICK_ACCOUNT_MODEL)


class ClickTransaction(models.Model):
    CREATED = 0
    INITIATING = 1
    SUCCESSFULLY = 2
    CANCELLED = -2

    STATE = [
        (CREATED, "Created"),
        (INITIATING, "Initiating"),
        (SUCCESSFULLY, "Successfully"),
        (CANCELLED, "Cancelled"),
    ]

    STATE_DICT = dict(STATE)

    state = models.IntegerField(choices=STATE, default=CREATED)
    transaction_id = models.CharField(max_length=255, unique=True)
    account_id = models.BigIntegerField(null=False)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"ClickTransaction(id={self.id}, state={self.get_state_display()})"

    @classmethod
    def get_or_create(cls, account_id, transaction_id, amount, state=None):
        defaults = {"state": state if state is not None else cls.INITIATING, "amount": amount}
        transaction, created = cls.objects.get_or_create(
            transaction_id=transaction_id,
            defaults={**defaults, "account_id": account_id},
        )
        return transaction
