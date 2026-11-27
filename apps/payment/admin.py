from django.contrib import admin
from .models import ClickTransaction, MerchatTransactionsModel, UzumBankTransactionsModel, CustomerCard, AtmosTransaction, AtmosRefund
from unfold.admin import ModelAdmin
from apps.base.admin_actions import activate, deactivate, mark_default, get_model_fields


@admin.register(CustomerCard)
class CustomerCardAdmin(ModelAdmin):
    list_display = get_model_fields(CustomerCard)
    list_filter = ('is_default', 'is_active', 'created_at')
    search_fields = ('user__full_name', 'user__phone_number', 'card_id')
    autocomplete_fields = ('user',)
    ordering = ('-created_at',)
    date_hierarchy = "created_at"
    actions = [activate, deactivate, mark_default]


@admin.register(ClickTransaction)
class ClickTransactionAdmin(ModelAdmin):
    list_display = get_model_fields(ClickTransaction)
    list_filter = ('state', 'created_at')
    search_fields = ('transaction_id', 'account_id')
    list_per_page = 25


@admin.register(MerchatTransactionsModel)
class MerchatTransactionsAdmin(ModelAdmin):
    list_display = get_model_fields(MerchatTransactionsModel)
    list_filter = ('state', 'created_at')
    search_fields = ('transaction_id', 'order_id', '_id')
    list_per_page = 25


@admin.register(UzumBankTransactionsModel)
class UzumBankTransactionsAdmin(ModelAdmin):
    list_display = get_model_fields(UzumBankTransactionsModel)
    list_filter = ('status', 'created_at')
    search_fields = ('trans_id', 'order_id')
    list_per_page = 25


@admin.register(AtmosTransaction)
class AtmosTransactionAdmin(ModelAdmin):
    list_display = get_model_fields(AtmosTransaction)
    list_filter = ('confirmed', 'status_code', 'created_at')
    search_fields = ('trans_id', 'account', 'order__id')
    autocomplete_fields = ('order',)
    ordering = ('-created_at',)
    list_per_page = 25


@admin.register(AtmosRefund)
class AtmosRefundAdmin(ModelAdmin):
    """Read-only: a refund is made in the admin panel (`orders/<id>/refunds/`), it moves money."""
    list_display = ('id', 'order', 'amount', 'status', 'partial_reverse_id', 'created_by', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order__id', 'partial_reverse_id')
    ordering = ('-created_at',)
    list_per_page = 25

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
