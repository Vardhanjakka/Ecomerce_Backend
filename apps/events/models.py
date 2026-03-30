from django.db import models


class EventStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    PROCESSED = 'PROCESSED', 'Processed'
    FAILED = 'FAILED', 'Failed'


class Event(models.Model):
    """
    Task 14: Event-Driven System
    Simulates an event queue: ORDER_CREATED, PAYMENT_SUCCESS, INVENTORY_UPDATED
    Rules: events must execute in order; failure stops next events
    """
    EVENT_TYPES = [
        ('ORDER_CREATED', 'Order Created'),
        ('ORDER_CANCELLED', 'Order Cancelled'),
        ('PAYMENT_SUCCESS', 'Payment Success'),
        ('PAYMENT_FAILED', 'Payment Failed'),
        ('INVENTORY_UPDATED', 'Inventory Updated'),
        ('STOCK_RESERVED', 'Stock Reserved'),
        ('STOCK_RELEASED', 'Stock Released'),
        ('FRAUD_DETECTED', 'Fraud Detected'),
    ]

    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, db_index=True)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=EventStatus.choices, default=EventStatus.PENDING)
    error_message = models.TextField(blank=True)
    sequence = models.PositiveIntegerField(default=0)  # enforce ordering
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['sequence', 'created_at']

    def __str__(self):
        return f"[{self.sequence}] {self.event_type} ({self.status})"
