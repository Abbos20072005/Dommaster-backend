from django.contrib import admin
from .models import ClickTransaction


@admin.register(ClickTransaction)
class ClickTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'account_id','transaction_id', 'amount')
    list_filter = ('account_id','transaction_id','created_at',)