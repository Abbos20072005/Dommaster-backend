from django.contrib import admin
from .models import ClickTransaction, MerchatTransactionsModel, UzumBankTransactionsModel, CustomerCard, AtmosTransaction
from unfold.admin import ModelAdmin

@admin.register(CustomerCard)
class CustomerCardAdmin(ModelAdmin):
    list_display = ('id', 'user', 'card_id', 'is_default', 'is_active')
    list_filter = ('user', 'card_id', 'is_default', 'is_active')
    search_fields = ('user', 'card_id')
    ordering = ('-created_at',)


@admin.register(ClickTransaction)
class ClickTransactionAdmin(ModelAdmin):
    list_display = ('id', 'account_id', 'transaction_id', 'amount')
    list_filter = ('account_id', 'transaction_id', 'created_at',)


@admin.register(MerchatTransactionsModel)
class MerchatTransactionsAdmin(ModelAdmin):
    list_display = ('id', 'transaction_id', 'amount', 'order_id')
    list_filter = ('transaction_id', 'created_at', 'order_id')


@admin.register(UzumBankTransactionsModel)
class UzumBankTransactionsAdmin(ModelAdmin):
    list_display = ('id', 'trans_id', 'amount', 'order_id')
    list_filter = ('trans_id', 'created_at', 'order_id')


@admin.register(AtmosTransaction)
class AtmosTransactionAdmin(ModelAdmin):
    list_display = ('id', 'order', 'trans_id', 'amount', 'confirmed', 'status_message', 'created_at')
    list_filter = ('confirmed', 'status_code', 'created_at')
    search_fields = ('trans_id', 'account', 'order__id')
    ordering = ('-created_at',)