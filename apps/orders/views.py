from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.models import User
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import Order, OrderItem, OrderStatus
from .serializers import OrderSerializer, PlaceOrderSerializer, TransitionOrderSerializer, ReturnItemSerializer
from apps.cart.models import Cart, CartItem
from apps.cart.views import apply_discount_rules
from apps.products.models import Product
from apps.logs.utils import write_log
from apps.events.utils import dispatch_event


def check_fraud(user, total):
    """Task 17: Fraud Detection"""
    from datetime import timedelta
    from django.conf import settings

    one_minute_ago = timezone.now() - timedelta(minutes=1)
    recent_orders = Order.objects.filter(user=user, created_at__gte=one_minute_ago).count()
    threshold = getattr(settings, 'FRAUD_ORDERS_PER_MINUTE', 3)
    high_value = getattr(settings, 'FRAUD_HIGH_VALUE_THRESHOLD', 10000)

    if recent_orders >= threshold:
        return True, f"Suspicious: {recent_orders} orders placed in last 1 minute"
    if total >= Decimal(str(high_value)):
        return True, f"Suspicious: High-value order ₹{total}"
    return False, ""


class OrderViewSet(viewsets.ModelViewSet):
    """
    Tasks 5, 7, 8, 11, 12, 13, 17, 19
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'is_flagged']
    search_fields = ['order_id']
    ordering_fields = ['created_at', 'total']

    def get_queryset(self):
        """Task 11: View own orders; admin sees all"""
        user = self.request.user
        if user.is_staff:
            return Order.objects.all().prefetch_related('items')
        return Order.objects.filter(user=user).prefetch_related('items')

    @action(detail=False, methods=['post'], url_path='place')
    def place_order(self, request):
        """
        Task 5: Order Placement Engine (atomic)
        Task 7: Transaction Rollback on failure
        Task 9: Discount & Coupon
        Task 17: Fraud Detection
        Task 19: Idempotency
        """
        serializer = PlaceOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        coupon_code = serializer.validated_data.get('coupon_code', '')
        idempotency_key = serializer.validated_data.get('idempotency_key', '')

        # Task 19: Idempotency - prevent duplicate orders
        if idempotency_key:
            existing = Order.objects.filter(idempotency_key=idempotency_key).first()
            if existing:
                write_log(user=request.user, action='DUPLICATE_ORDER_BLOCKED',
                          details=f"Idempotency key {idempotency_key} already used for order {existing.order_id}")
                return Response(
                    {'message': 'Order already placed.', 'order': OrderSerializer(existing).data},
                    status=status.HTTP_200_OK
                )

        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            return Response({'error': 'Cart not found.'}, status=status.HTTP_400_BAD_REQUEST)

        cart_items = list(cart.items.select_related('product').all())
        if not cart_items:
            return Response({'error': 'Cart is empty.'}, status=status.HTTP_400_BAD_REQUEST)

        # Task 5: Step 1 - Validate cart (check stock)
        for item in cart_items:
            if item.product.available_stock < item.quantity:
                return Response(
                    {'error': f"Insufficient stock for '{item.product.name}'. Available: {item.product.available_stock}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Task 5: Steps 2-5 wrapped in atomic transaction (Task 7: rollback on fail)
        try:
            with transaction.atomic():
                # Step 2: Calculate total
                subtotal = cart.total
                discount, final_total, applied = apply_discount_rules(
                    subtotal, cart_items, coupon_code if coupon_code else None
                )

                # Task 17: Fraud check
                is_flagged, flag_reason = check_fraud(request.user, final_total)

                # Step 3: Lock stock (select_for_update prevents race conditions - Task 4)
                for item in cart_items:
                    product = Product.objects.select_for_update().get(pk=item.product.pk)
                    if product.available_stock < item.quantity:
                        raise ValueError(f"Stock conflict for '{product.name}'. Someone just took the last units.")
                    product.stock -= item.quantity
                    product.reserved_stock = max(0, product.reserved_stock - item.quantity)
                    product.save(update_fields=['stock', 'reserved_stock', 'updated_at'])

                # Step 4: Create order
                order = Order.objects.create(
                    user=request.user,
                    status=OrderStatus.CREATED,
                    subtotal=subtotal,
                    discount=discount,
                    total=final_total,
                    coupon_code=coupon_code or None,
                    is_flagged=is_flagged,
                    flag_reason=flag_reason,
                    idempotency_key=idempotency_key or None,
                )

                for item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        product_id_str=item.product.product_id,
                        product_name=item.product.name,
                        unit_price=item.product.price,
                        quantity=item.quantity,
                    )

                # Step 5: Clear cart
                cart.clear()

                # Transition to PENDING_PAYMENT
                order.transition_to(OrderStatus.PENDING_PAYMENT)

                write_log(user=request.user, action='ORDER_CREATED',
                          details=f"ORDER_{order.order_id} created. Total=₹{final_total}. Flagged={is_flagged}")

                # Task 14: Dispatch event
                dispatch_event('ORDER_CREATED', {
                    'order_id': str(order.order_id),
                    'user': request.user.username,
                    'total': str(final_total),
                })

                return Response({
                    'order': OrderSerializer(order).data,
                    'applied_discounts': applied,
                    'flagged': is_flagged,
                    'flag_reason': flag_reason,
                }, status=status.HTTP_201_CREATED)

        except ValueError as e:
            # Task 7: Transaction rolled back automatically
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='transition')
    def transition(self, request, pk=None):
        """Task 8: Order State Machine - transition to new status"""
        order = self.get_object()
        serializer = TransitionOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data['new_status']
        try:
            order.transition_to(new_status)
            write_log(user=request.user, action='ORDER_STATUS_CHANGED',
                      details=f"Order {order.order_id} transitioned to {new_status}")
            return Response(OrderSerializer(order).data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel_order(self, request, pk=None):
        """Task 12: Order Cancellation Engine"""
        order = self.get_object()

        # Task 12: Cannot cancel already cancelled order
        if order.status == OrderStatus.CANCELLED:
            return Response({'error': 'Order is already cancelled.'}, status=status.HTTP_400_BAD_REQUEST)

        if not order.can_transition_to(OrderStatus.CANCELLED):
            return Response(
                {'error': f'Cannot cancel order in status: {order.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            # Restore stock
            for item in order.items.select_related('product').all():
                if item.product:
                    product = Product.objects.select_for_update().get(pk=item.product.pk)
                    product.stock += item.quantity
                    product.save(update_fields=['stock', 'updated_at'])

            order.transition_to(OrderStatus.CANCELLED)

        write_log(user=request.user, action='ORDER_CANCELLED',
                  details=f"Order {order.order_id} cancelled. Stock restored.")
        dispatch_event('ORDER_CANCELLED', {'order_id': str(order.order_id)})

        return Response({'message': 'Order cancelled and stock restored.', 'order': OrderSerializer(order).data})

    @action(detail=True, methods=['post'], url_path='return')
    def return_order(self, request, pk=None):
        """Task 13: Return & Refund System (partial return)"""
        order = self.get_object()

        if order.status != OrderStatus.DELIVERED:
            return Response({'error': 'Only delivered orders can be returned.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ReturnItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return_items = serializer.validated_data['items']  # [{order_item_id: qty}, ...]
        total_refund = Decimal('0')

        with transaction.atomic():
            for entry in return_items:
                for item_id_str, qty in entry.items():
                    try:
                        order_item = OrderItem.objects.select_for_update().get(
                            pk=int(item_id_str), order=order
                        )
                    except OrderItem.DoesNotExist:
                        return Response({'error': f'Item {item_id_str} not found in order.'}, status=400)

                    if qty > order_item.returnable_quantity:
                        return Response(
                            {'error': f'Cannot return {qty} of item {item_id_str}. Max returnable: {order_item.returnable_quantity}'},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                    # Update returned qty
                    order_item.returned_quantity += qty
                    order_item.save(update_fields=['returned_quantity'])

                    # Restore stock
                    if order_item.product:
                        product = Product.objects.select_for_update().get(pk=order_item.product.pk)
                        product.stock += qty
                        product.save(update_fields=['stock', 'updated_at'])

                    refund_amount = order_item.unit_price * qty
                    total_refund += refund_amount

            # Update order total
            order.total = max(Decimal('0'), order.total - total_refund)
            order.status = OrderStatus.RETURNED
            order.save(update_fields=['total', 'status', 'updated_at'])

        write_log(user=request.user, action='ORDER_RETURNED',
                  details=f"Order {order.order_id} partial return. Refund=₹{total_refund}")

        return Response({
            'message': 'Return processed successfully.',
            'refund_amount': str(total_refund),
            'order': OrderSerializer(order).data,
        })
