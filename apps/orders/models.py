from django.db import models
from django.contrib.auth.models import User
from apps.products.models import Product
import uuid


class OrderStatus(models.TextChoices):
    """Task 8: Order State Machine"""
    CREATED = 'CREATED', 'Created'
    PENDING_PAYMENT = 'PENDING_PAYMENT', 'Pending Payment'
    PAID = 'PAID', 'Paid'
    SHIPPED = 'SHIPPED', 'Shipped'
    DELIVERED = 'DELIVERED', 'Delivered'
    FAILED = 'FAILED', 'Failed'
    CANCELLED = 'CANCELLED', 'Cancelled'
    RETURNED = 'RETURNED', 'Returned'


# Task 8: Valid state transitions
VALID_TRANSITIONS = {
    OrderStatus.CREATED: [OrderStatus.PENDING_PAYMENT, OrderStatus.CANCELLED],
    OrderStatus.PENDING_PAYMENT: [OrderStatus.PAID, OrderStatus.FAILED, OrderStatus.CANCELLED],
    OrderStatus.PAID: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
    OrderStatus.SHIPPED: [OrderStatus.DELIVERED],
    OrderStatus.DELIVERED: [OrderStatus.RETURNED],
    OrderStatus.FAILED: [],
    OrderStatus.CANCELLED: [],
    OrderStatus.RETURNED: [],
}


class Order(models.Model):
    """Task 5: Order Placement Engine | Task 8: State Machine | Task 11: Order Management"""
    order_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.CREATED)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    coupon_code = models.CharField(max_length=50, blank=True, null=True)

    # Task 17: Fraud detection flag
    is_flagged = models.BooleanField(default=False)
    flag_reason = models.CharField(max_length=255, blank=True)

    # Task 19: Idempotency key to prevent duplicate orders
    idempotency_key = models.CharField(max_length=255, unique=True, null=True, blank=True)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.order_id} [{self.status}] by {self.user.username}"

    def can_transition_to(self, new_status):
        """Task 8: Validate state transition"""
        allowed = VALID_TRANSITIONS.get(self.status, [])
        return new_status in allowed

    def transition_to(self, new_status, save=True):
        """Task 8: Perform state transition with validation"""
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Invalid transition: {self.status} → {new_status}. "
                f"Allowed: {VALID_TRANSITIONS.get(self.status, [])}"
            )
        self.status = new_status
        if save:
            self.save(update_fields=['status', 'updated_at'])


class OrderItem(models.Model):
    """Individual line item in an order"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    product_id_str = models.CharField(max_length=100)  # preserve even if product deleted
    product_name = models.CharField(max_length=255)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    returned_quantity = models.PositiveIntegerField(default=0)  # Task 13: partial return

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.product_id_str} x{self.quantity} in Order {self.order.order_id}"

    @property
    def subtotal(self):
        return self.unit_price * self.quantity

    @property
    def returnable_quantity(self):
        return self.quantity - self.returned_quantity
