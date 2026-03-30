from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product_id_str', 'product_name', 'unit_price', 'quantity', 'returned_quantity', 'subtotal', 'returnable_quantity']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'user', 'status', 'total', 'is_flagged', 'created_at']
    list_filter = ['status', 'is_flagged']
    search_fields = ['order_id', 'user__username']
    readonly_fields = ['order_id', 'created_at', 'updated_at']
    inlines = [OrderItemInline]
