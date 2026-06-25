from django.contrib import admin
from .models import ClickTransaction, MerchatTransactionsModel, UzumBankTransactionsModel, CustomerCard, AtmosTransaction
from unfold.admin import ModelAdmin


@admin.register(CustomerCard)
class CustomerCardAdmin(ModelAdmin):
    list_display = ('id', 'user', 'card_id', 'is_default', 'is_active', 'created_at')
    list_filter = ('is_default', 'is_active', 'created_at')
    search_fields = ('user__full_name', 'user__phone_number', 'card_id')
    autocomplete_fields = ('user',)
    ordering = ('-created_at',)
    date_hierarchy = "created_at"


@admin.register(ClickTransaction)
class ClickTransactionAdmin(ModelAdmin):
    list_display = ('id', 'account_id', 'transaction_id', 'amount', 'state', 'created_at')
    list_filter = ('state', 'created_at')
    search_fields = ('transaction_id', 'account_id')
    list_per_page = 25


@admin.register(MerchatTransactionsModel)
class MerchatTransactionsAdmin(ModelAdmin):
    list_display = ('id', 'transaction_id', 'amount', 'order_id', 'state', 'created_at')
    list_filter = ('state', 'created_at')
    search_fields = ('transaction_id', 'order_id', '_id')
    list_per_page = 25


@admin.register(UzumBankTransactionsModel)
class UzumBankTransactionsAdmin(ModelAdmin):
    list_display = ('id', 'trans_id', 'amount', 'order_id', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('trans_id', 'order_id')
    list_per_page = 25


@admin.register(AtmosTransaction)
class AtmosTransactionAdmin(ModelAdmin):
    list_display = ('id', 'order', 'trans_id', 'amount', 'confirmed', 'status_code', 'status_message', 'created_at')
    list_filter = ('confirmed', 'status_code', 'created_at')
    search_fields = ('trans_id', 'account', 'order__id')
    autocomplete_fields = ('order',)
    ordering = ('-created_at',)
    list_per_page = 25
