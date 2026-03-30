from rest_framework import serializers
from .models import Order, OrderItem, OrderStatus, VALID_TRANSITIONS


class OrderItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.ReadOnlyField()
    returnable_quantity = serializers.ReadOnlyField()

    class Meta:
        model = OrderItem
        fields = [
            'id', 'product_id_str', 'product_name',
            'unit_price', 'quantity', 'returned_quantity',
            'returnable_quantity', 'subtotal'
        ]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    order_id = serializers.UUIDField(read_only=True)
    allowed_transitions = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'order_id', 'username', 'status', 'subtotal',
            'discount', 'total', 'coupon_code', 'is_flagged', 'flag_reason',
            'items', 'allowed_transitions', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'order_id', 'created_at', 'updated_at', 'is_flagged', 'flag_reason']

    def get_allowed_transitions(self, obj):
        return VALID_TRANSITIONS.get(obj.status, [])


class PlaceOrderSerializer(serializers.Serializer):
    """Task 5: Place Order"""
    coupon_code = serializers.CharField(required=False, allow_blank=True)
    idempotency_key = serializers.CharField(required=False, allow_blank=True)  # Task 19


class TransitionOrderSerializer(serializers.Serializer):
    """Task 8: State transition"""
    new_status = serializers.ChoiceField(choices=OrderStatus.choices)


class ReturnItemSerializer(serializers.Serializer):
    """Task 13: Return & Refund"""
    items = serializers.ListField(
        child=serializers.DictField(child=serializers.IntegerField()),
        help_text="List of {order_item_id: quantity} to return"
    )
