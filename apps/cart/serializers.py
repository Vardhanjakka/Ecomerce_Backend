from rest_framework import serializers
from .models import Cart, CartItem
from apps.products.serializers import ProductSerializer


class CartItemSerializer(serializers.ModelSerializer):
    product_detail = ProductSerializer(source='product', read_only=True)
    subtotal = serializers.ReadOnlyField()
    product_id = serializers.CharField(write_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'product_id', 'product_detail', 'quantity', 'subtotal', 'added_at', 'updated_at']
        read_only_fields = ['id', 'added_at', 'updated_at']

    def validate_product_id(self, value):
        from apps.products.models import Product
        try:
            product = Product.objects.get(product_id=value, is_active=True)
        except Product.DoesNotExist:
            raise serializers.ValidationError(f"Product '{value}' not found or inactive.")
        return value


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.ReadOnlyField()
    item_count = serializers.ReadOnlyField()
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'username', 'items', 'total', 'item_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class AddToCartSerializer(serializers.Serializer):
    product_id = serializers.CharField()
    quantity = serializers.IntegerField(min_value=1, default=1)

    def validate_product_id(self, value):
        from apps.products.models import Product
        try:
            Product.objects.get(product_id=value, is_active=True)
        except Product.DoesNotExist:
            raise serializers.ValidationError(f"Product '{value}' not found.")
        return value


class ApplyCouponSerializer(serializers.Serializer):
    """Task 9: Discount & Coupon Engine"""
    coupon_code = serializers.CharField()
