from decimal import Decimal
from rest_framework import status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Cart, CartItem
from .serializers import CartSerializer, AddToCartSerializer, ApplyCouponSerializer
from apps.products.models import Product
from apps.logs.utils import write_log

# Task 9: Coupon definitions
COUPONS = {
    'SAVE10': {'type': 'percent', 'value': Decimal('10')},
    'FLAT200': {'type': 'flat', 'value': Decimal('200')},
}


def get_or_create_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


def apply_discount_rules(total, items, coupon_code=None):
    """Task 9: Discount & Coupon Engine"""
    discount = Decimal('0')
    applied = []

    # Rule 1: Total > 1000 → 10% discount
    if total > Decimal('1000'):
        d = total * Decimal('0.10')
        discount += d
        applied.append(f"10% discount for order > ₹1000 (-₹{d:.2f})")

    # Rule 2: Quantity > 3 same product → extra 5%
    for item in items:
        if item.quantity > 3:
            d = item.subtotal * Decimal('0.05')
            discount += d
            applied.append(f"5% bulk discount on {item.product.name} (-₹{d:.2f})")

    # Rule 3: Coupon codes
    if coupon_code and coupon_code.upper() in COUPONS:
        coupon = COUPONS[coupon_code.upper()]
        if coupon['type'] == 'percent':
            d = total * (coupon['value'] / 100)
        else:
            d = coupon['value']
        discount += d
        applied.append(f"Coupon {coupon_code.upper()} applied (-₹{d:.2f})")
    elif coupon_code:
        applied.append(f"Coupon '{coupon_code}' is invalid.")

    final_total = max(Decimal('0'), total - discount)
    return discount, final_total, applied


class CartView(views.APIView):
    """Task 2: View cart"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart = get_or_create_cart(request.user)
        return Response(CartSerializer(cart).data)


class AddToCartView(views.APIView):
    """Task 2 + Task 3: Add to cart with stock reservation check"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product_id = serializer.validated_data['product_id']
        quantity = serializer.validated_data['quantity']
        product = Product.objects.get(product_id=product_id, is_active=True)

        # Task 10: Block if stock = 0
        if product.available_stock <= 0:
            return Response({'error': f"'{product.name}' is out of stock."}, status=status.HTTP_400_BAD_REQUEST)

        # Task 2: Cannot add more than available stock
        if quantity > product.available_stock:
            return Response(
                {'error': f"Only {product.available_stock} units available."},
                status=status.HTTP_400_BAD_REQUEST
            )

        cart = get_or_create_cart(request.user)
        item, created = CartItem.objects.get_or_create(cart=cart, product=product, defaults={'quantity': quantity})

        if not created:
            new_qty = item.quantity + quantity
            if new_qty > product.available_stock:
                return Response({'error': f"Cannot add more. Only {product.available_stock} available."}, status=400)
            item.quantity = new_qty
            item.save(update_fields=['quantity', 'updated_at'])

        write_log(user=request.user, action='CART_ITEM_ADDED',
                  details=f"{request.user.username} added {product.product_id} qty={quantity} to cart")
        return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)


class RemoveFromCartView(views.APIView):
    """Task 2: Remove from cart"""
    permission_classes = [IsAuthenticated]

    def delete(self, request, product_id):
        cart = get_or_create_cart(request.user)
        try:
            item = CartItem.objects.get(cart=cart, product__product_id=product_id)
            item.delete()
            write_log(user=request.user, action='CART_ITEM_REMOVED',
                      details=f"{request.user.username} removed {product_id} from cart")
            return Response({'message': f'Removed {product_id} from cart.'})
        except CartItem.DoesNotExist:
            return Response({'error': 'Item not found in cart.'}, status=status.HTTP_404_NOT_FOUND)


class UpdateCartItemView(views.APIView):
    """Task 2: Update quantity"""
    permission_classes = [IsAuthenticated]

    def patch(self, request, product_id):
        quantity = int(request.data.get('quantity', 1))
        cart = get_or_create_cart(request.user)

        try:
            item = CartItem.objects.get(cart=cart, product__product_id=product_id)
            if quantity <= 0:
                item.delete()
                return Response({'message': 'Item removed from cart.'})
            if quantity > item.product.available_stock:
                return Response({'error': f"Only {item.product.available_stock} available."}, status=400)
            item.quantity = quantity
            item.save(update_fields=['quantity', 'updated_at'])
            return Response(CartSerializer(cart).data)
        except CartItem.DoesNotExist:
            return Response({'error': 'Item not found in cart.'}, status=status.HTTP_404_NOT_FOUND)


class ApplyCouponView(views.APIView):
    """Task 9: Apply coupon and show discount breakdown"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ApplyCouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart = get_or_create_cart(request.user)
        items = list(cart.items.select_related('product').all())
        total = cart.total
        coupon_code = serializer.validated_data['coupon_code']

        discount, final_total, applied = apply_discount_rules(total, items, coupon_code)
        write_log(user=request.user, action='COUPON_APPLIED',
                  details=f"{request.user.username} applied coupon {coupon_code}. Discount=₹{discount:.2f}")

        return Response({
            'subtotal': str(total),
            'discount': str(discount),
            'final_total': str(final_total),
            'applied_discounts': applied,
            'coupon_code': coupon_code.upper() if coupon_code.upper() in COUPONS else None,
        })


class CartSummaryView(views.APIView):
    """Cart summary with auto discount (no coupon)"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart = get_or_create_cart(request.user)
        items = list(cart.items.select_related('product').all())
        total = cart.total
        discount, final_total, applied = apply_discount_rules(total, items)
        return Response({
            'cart': CartSerializer(cart).data,
            'subtotal': str(total),
            'discount': str(discount),
            'final_total': str(final_total),
            'applied_discounts': applied,
        })
