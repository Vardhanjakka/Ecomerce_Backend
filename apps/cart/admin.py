from django.contrib import admin
from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['subtotal', 'added_at', 'updated_at']


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'item_count', 'total', 'updated_at']
    readonly_fields = ['total', 'item_count', 'created_at', 'updated_at']
    inlines = [CartItemInline]
