import random
from decimal import Decimal
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers

from .models import Payment, PaymentStatus
from apps.orders.models import Order, OrderStatus
from apps.products.models import Product
from apps.logs.utils import write_log
from apps.events.utils import dispatch_event


class PaymentSerializer(serializers.ModelSerializer):
    order_id = serializers.UUIDField(source='order.order_id', read_only=True)

    class Meta:
        model = Payment
        fields = ['id', 'payment_id', 'order_id', 'amount', 'status',
                  'failure_reason', 'failure_injected', 'attempt_number', 'created_at']


class ProcessPaymentSerializer(serializers.Serializer):
    order_id = serializers.UUIDField()
    force_fail = serializers.BooleanField(default=False)   # Task 18: injection
    force_succeed = serializers.BooleanField(default=False)


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """Task 6: Payment Simulation | Task 7: Rollback | Task 18: Failure Injection"""
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Payment.objects.all()
        return Payment.objects.filter(order__user=self.request.user)

    @action(detail=False, methods=['post'], url_path='process')
    def process_payment(self, request):
        """
        Task 6: Simulate payment (success/failure)
        Task 7: Rollback on failure — restore stock, cancel order
        Task 18: Failure injection via force_fail flag
        """
        serializer = ProcessPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order_id = serializer.validated_data['order_id']
        force_fail = serializer.validated_data['force_fail']
        force_succeed = serializer.validated_data['force_succeed']

        try:
            order = Order.objects.get(order_id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

        if order.status != OrderStatus.PENDING_PAYMENT:
            return Response({'error': f'Order is not pending payment. Current status: {order.status}'}, status=400)

        attempt = Payment.objects.filter(order=order).count() + 1

        # Task 6: Simulate outcome
        # Task 18: Failure injection overrides random
        if force_fail:
            payment_success = False
            failure_reason = "Failure injected manually (Task 18)"
            injected = True
        elif force_succeed:
            payment_success = True
            failure_reason = ""
            injected = True
        else:
            # Task 18: Random failure for payment/order_creation/inventory_update (30% fail rate)
            payment_success = random.random() > 0.3
            failure_reason = "Payment gateway timeout" if not payment_success else ""
            injected = False

        with transaction.atomic():
            payment = Payment.objects.create(
                order=order,
                amount=order.total,
                status=PaymentStatus.SUCCESS if payment_success else PaymentStatus.FAILED,
                failure_reason=failure_reason,
                failure_injected=injected,
                attempt_number=attempt,
            )

            if payment_success:
                # Task 6: Payment success → update order state
                order.transition_to(OrderStatus.PAID)
                write_log(user=request.user, action='PAYMENT_SUCCESS',
                          details=f"Payment {payment.payment_id} SUCCESS for order {order.order_id} ₹{order.total}")
                dispatch_event('PAYMENT_SUCCESS', {
                    'order_id': str(order.order_id),
                    'payment_id': str(payment.payment_id),
                    'amount': str(order.total),
                })
                return Response({
                    'result': 'success',
                    'payment': PaymentSerializer(payment).data,
                    'order_status': order.status,
                })

            else:
                # Task 7: Transaction Rollback — restore stock, cancel order
                for item in order.items.select_related('product').all():
                    if item.product:
                        product = Product.objects.select_for_update().get(pk=item.product.pk)
                        product.stock += item.quantity
                        product.save(update_fields=['stock', 'updated_at'])

                order.transition_to(OrderStatus.FAILED)
                write_log(user=request.user, action='PAYMENT_FAILED',
                          details=f"Payment FAILED for order {order.order_id}. Reason: {failure_reason}. Stock restored.")
                dispatch_event('PAYMENT_FAILED', {
                    'order_id': str(order.order_id),
                    'reason': failure_reason,
                })
                return Response({
                    'result': 'failed',
                    'reason': failure_reason,
                    'payment': PaymentSerializer(payment).data,
                    'order_status': order.status,
                    'rollback': 'Stock restored. Order marked FAILED.',
                }, status=status.HTTP_402_PAYMENT_REQUIRED)

    @action(detail=False, methods=['post'], url_path='inject-failure')
    def inject_failure(self, request):
        """Task 18: Failure Injection System - test random failures"""
        component = request.data.get('component', 'payment')
        valid_components = ['payment', 'order_creation', 'inventory_update']
        if component not in valid_components:
            return Response({'error': f'Component must be one of: {valid_components}'}, status=400)

        should_fail = random.random() > 0.5
        write_log(user=request.user, action='FAILURE_INJECTED',
                  details=f"Failure injection test on '{component}': {'FAILED' if should_fail else 'PASSED'}")
        return Response({
            'component': component,
            'injected_failure': should_fail,
            'message': f"Simulated {'FAILURE' if should_fail else 'SUCCESS'} for component: {component}"
        })
