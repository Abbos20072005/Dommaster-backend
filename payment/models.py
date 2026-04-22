from django.conf import settings
from django.db import models
from django.utils.module_loading import import_string
from authorization.models import Customer

AccountModel = import_string(settings.CLICK_ACCOUNT_MODEL)

UzumBankStatus = (
    ('CREATED', "CREATED"),
    ('CONFIRMED', "CONFIRMED"),
    ('REVERSED', "REVERSED")
)


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


class MerchatTransactionsModel(models.Model):
    _id = models.CharField(max_length=255, null=True, blank=False)
    transaction_id = models.CharField(max_length=255, null=True, blank=False)
    order_id = models.BigIntegerField(null=True, blank=True)
    amount = models.FloatField(null=True, blank=True)
    time = models.BigIntegerField(null=True, blank=True)
    perform_time = models.BigIntegerField(null=True, default=0)
    cancel_time = models.BigIntegerField(null=True, default=0)
    state = models.IntegerField(null=True, default=1)
    reason = models.CharField(max_length=255, null=True, blank=True)
    created_at_ms = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self._id)


class UzumBankTransactionsModel(models.Model):
    trans_id = models.CharField(max_length=255, null=True, blank=True)
    order_id = models.BigIntegerField(null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=11, choices=UzumBankStatus)
    trans_time = models.BigIntegerField(null=True, blank=True)
    confirm_time = models.BigIntegerField(null=True, blank=True)
    reverse_time = models.BigIntegerField(null=True, blank=True)
    payment_source=models.CharField(max_length=100, null=True, blank=True)
    tariff=models.CharField(max_length=50, null=True, blank=True)
    processing_reference_number=models.CharField(max_length=50, null=True, blank=True)
    phone=models.CharField(max_length=50, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.trans_id)

class CustomerCard(models.Model):
    user = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="cards")
    card_id = models.CharField(max_length=255, unique=True)
    token = models.CharField(max_length=255, blank=True, null=True)
    pan = models.CharField(max_length=255, blank=True, null=True)
    card_holder = models.CharField(max_length=255, blank=True, null=True)
    expiry = models.CharField(max_length=10, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} — {self.pan or self.card_id}"