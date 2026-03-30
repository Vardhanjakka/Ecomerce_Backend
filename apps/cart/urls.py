from django.urls import path
from .views import (
    CartView, AddToCartView, RemoveFromCartView,
    UpdateCartItemView, ApplyCouponView, CartSummaryView
)

urlpatterns = [
    path('', CartView.as_view(), name='cart-view'),
    path('add/', AddToCartView.as_view(), name='cart-add'),
    path('remove/<str:product_id>/', RemoveFromCartView.as_view(), name='cart-remove'),
    path('update/<str:product_id>/', UpdateCartItemView.as_view(), name='cart-update'),
    path('apply-coupon/', ApplyCouponView.as_view(), name='cart-apply-coupon'),
    path('summary/', CartSummaryView.as_view(), name='cart-summary'),
]
