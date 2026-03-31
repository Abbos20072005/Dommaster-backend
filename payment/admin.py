from django.contrib import admin
from .models import ClickTransaction, MerchatTransactionsModel, UzumBankTransactionsModel, CustomerCard

@admin.register(CustomerCard)
class CustomerCardAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'card_id', 'is_active')
    list_filter = ('user', 'card_id', 'is_active')
    search_fields = ('user', 'card_id')
    ordering = ('-created_at',)


@admin.register(ClickTransaction)
class ClickTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'account_id', 'transaction_id', 'amount')
    list_filter = ('account_id', 'transaction_id', 'created_at',)


@admin.register(MerchatTransactionsModel)
class MerchatTransactionsAdmin(admin.ModelAdmin):
    list_display = ('id', 'transaction_id', 'amount', 'order_id')
    list_filter = ('transaction_id', 'created_at', 'order_id')


@admin.register(UzumBankTransactionsModel)
class UzumBankTransactionsAdmin(admin.ModelAdmin):
    list_display = ('id', 'trans_id', 'amount', 'order_id')
    list_filter = ('trans_id', 'created_at', 'order_id')