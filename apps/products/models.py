from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone


class Product(models.Model):
    """Task 1: Product Management"""
    product_id = models.CharField(max_length=100, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    stock = models.PositiveIntegerField(default=0)
    reserved_stock = models.PositiveIntegerField(default=0)  # Task 3: Real-Time Stock Reservation
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product_id} - {self.name}"

    @property
    def available_stock(self):
        """Task 3: Available = total - reserved"""
        return self.stock - self.reserved_stock

    @property
    def is_low_stock(self):
        """Task 10: Low stock alert threshold"""
        return self.stock <= 5

    def reserve_stock(self, quantity):
        """Task 3: Reserve stock atomically"""
        from django.db import transaction
        with transaction.atomic():
            product = Product.objects.select_for_update().get(pk=self.pk)
            if product.available_stock < quantity:
                raise ValueError(f"Insufficient stock. Available: {product.available_stock}, Requested: {quantity}")
            product.reserved_stock += quantity
            product.save(update_fields=['reserved_stock', 'updated_at'])
        self.refresh_from_db()

    def release_stock(self, quantity):
        """Task 3: Release reserved stock"""
        from django.db import transaction
        with transaction.atomic():
            product = Product.objects.select_for_update().get(pk=self.pk)
            product.reserved_stock = max(0, product.reserved_stock - quantity)
            product.save(update_fields=['reserved_stock', 'updated_at'])
        self.refresh_from_db()

    def deduct_stock(self, quantity):
        """Permanently deduct stock after order confirmed"""
        from django.db import transaction
        with transaction.atomic():
            product = Product.objects.select_for_update().get(pk=self.pk)
            product.stock = max(0, product.stock - quantity)
            product.reserved_stock = max(0, product.reserved_stock - quantity)
            product.save(update_fields=['stock', 'reserved_stock', 'updated_at'])
        self.refresh_from_db()


class StockReservation(models.Model):
    """Task 15: Inventory Reservation Expiry"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reservations')
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='reservations')
    quantity = models.PositiveIntegerField()
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['expires_at']

    def __str__(self):
        return f"Reservation: {self.product.product_id} x{self.quantity} by {self.user.username}"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    def release(self):
        """Release expired reservation back to available stock"""
        if self.is_active:
            self.product.release_stock(self.quantity)
            self.is_active = False
            self.save(update_fields=['is_active'])
