from django.contrib import admin
from .models import Product, StockReservation


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['product_id', 'name', 'price', 'stock', 'reserved_stock', 'available_stock', 'is_low_stock', 'is_active']
    list_filter = ['is_active']
    search_fields = ['product_id', 'name']
    readonly_fields = ['reserved_stock', 'available_stock', 'is_low_stock', 'created_at', 'updated_at']


@admin.register(StockReservation)
class StockReservationAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'quantity', 'expires_at', 'is_active', 'is_expired']
    list_filter = ['is_active']
    readonly_fields = ['created_at', 'is_expired']
