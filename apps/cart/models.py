from django.db import models
from django.contrib.auth.models import User
from apps.products.models import Product


class Cart(models.Model):
    """Task 2: Multi-User Cart System - each user has a separate cart"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart of {self.user.username}"

    @property
    def total(self):
        return sum(item.subtotal for item in self.items.all())

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())

    def clear(self):
        self.items.all().delete()


class CartItem(models.Model):
    """Task 2: Individual cart item"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['cart', 'product']
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.cart.user.username} -> {self.product.product_id} x{self.quantity}"

    @property
    def subtotal(self):
        return self.product.price * self.quantity
