from django.db import models
from apps.orders.models import Order
import uuid


class PaymentStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    SUCCESS = 'SUCCESS', 'Success'
    FAILED = 'FAILED', 'Failed'
    REFUNDED = 'REFUNDED', 'Refunded'


class Payment(models.Model):
    """Task 6: Payment Simulation | Task 18: Failure Injection"""
    payment_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    failure_reason = models.CharField(max_length=255, blank=True)
    failure_injected = models.BooleanField(default=False)  # Task 18
    attempt_number = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment {self.payment_id} [{self.status}] for Order {self.order.order_id}"
