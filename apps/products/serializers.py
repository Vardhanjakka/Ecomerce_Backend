from rest_framework import serializers
from .models import Product, StockReservation


class ProductSerializer(serializers.ModelSerializer):
    available_stock = serializers.ReadOnlyField()
    is_low_stock = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = [
            'id', 'product_id', 'name', 'description', 'price',
            'stock', 'reserved_stock', 'available_stock', 'is_low_stock',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'reserved_stock', 'created_at', 'updated_at']

    def validate_stock(self, value):
        if value < 0:
            raise serializers.ValidationError("Stock cannot be negative.")
        return value

    def validate_product_id(self, value):
        # Task 1: Prevent duplicate product IDs
        instance = self.instance
        qs = Product.objects.filter(product_id=value)
        if instance:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            raise serializers.ValidationError(f"Product with ID '{value}' already exists.")
        return value


class ProductUpdateStockSerializer(serializers.Serializer):
    quantity = serializers.IntegerField()
    operation = serializers.ChoiceField(choices=['add', 'subtract'], default='add')

    def validate(self, data):
        if data['operation'] == 'subtract' and data['quantity'] < 0:
            raise serializers.ValidationError("Quantity must be positive.")
        return data


class StockReservationSerializer(serializers.ModelSerializer):
    is_expired = serializers.ReadOnlyField()
    product_id = serializers.CharField(source='product.product_id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = StockReservation
        fields = ['id', 'product_id', 'username', 'quantity', 'expires_at', 'is_active', 'is_expired', 'created_at']
        read_only_fields = ['id', 'created_at', 'expires_at']


class LowStockProductSerializer(serializers.ModelSerializer):
    available_stock = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = ['id', 'product_id', 'name', 'stock', 'available_stock', 'reserved_stock']
