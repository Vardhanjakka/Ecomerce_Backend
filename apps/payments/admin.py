from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_id', 'order', 'amount', 'status', 'failure_injected', 'attempt_number', 'created_at']
    list_filter = ['status', 'failure_injected']
    readonly_fields = ['payment_id', 'created_at', 'updated_at']
