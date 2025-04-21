from django.contrib import admin
from .models import ClickTransaction, MerchatTransactionsModel


@admin.register(ClickTransaction)
class ClickTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'account_id', 'transaction_id', 'amount')
    list_filter = ('account_id', 'transaction_id', 'created_at',)


@admin.register(MerchatTransactionsModel)
class MerchatTransactionsAdmin(admin.ModelAdmin):
    list_display = ('id', 'transaction_id', 'amount', 'order_id')
    list_filter = ('transaction_id', 'created_at', 'order_id')
