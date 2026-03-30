from django.utils import timezone
from django.conf import settings
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from datetime import timedelta

from .models import Product, StockReservation
from .serializers import (
    ProductSerializer, ProductUpdateStockSerializer,
    StockReservationSerializer, LowStockProductSerializer
)
from apps.logs.utils import write_log


class ProductViewSet(viewsets.ModelViewSet):
    """
    Task 1: Product Management
    Task 3: Real-Time Stock Reservation
    Task 10: Inventory Alert System
    Task 15: Inventory Reservation Expiry
    """
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['product_id', 'name']
    ordering_fields = ['price', 'stock', 'created_at']

    def perform_create(self, serializer):
        product = serializer.save()
        write_log(
            user=self.request.user,
            action='PRODUCT_ADDED',
            details=f"Product {product.product_id} added with stock={product.stock}"
        )

    def perform_update(self, serializer):
        product = serializer.save()
        write_log(
            user=self.request.user,
            action='PRODUCT_UPDATED',
            details=f"Product {product.product_id} updated"
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def update_stock(self, request, pk=None):
        """Task 1: Update stock with add/subtract"""
        product = self.get_object()
        serializer = ProductUpdateStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        qty = serializer.validated_data['quantity']
        op = serializer.validated_data['operation']

        if op == 'subtract':
            if product.stock < qty:
                return Response({'error': 'Stock cannot go negative.'}, status=status.HTTP_400_BAD_REQUEST)
            product.stock -= qty
        else:
            product.stock += qty

        product.save(update_fields=['stock', 'updated_at'])
        write_log(user=request.user, action='STOCK_UPDATED',
                  details=f"Product {product.product_id} stock {op} {qty}. New stock={product.stock}")
        return Response(ProductSerializer(product).data)

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Task 10: Inventory Alert System - show low stock products"""
        products = Product.objects.filter(stock__lte=5, is_active=True)
        serializer = LowStockProductSerializer(products, many=True)
        return Response({'low_stock_products': serializer.data, 'count': products.count()})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def reserve(self, request, pk=None):
        """Task 3: Reserve stock for a user"""
        product = self.get_object()
        quantity = int(request.data.get('quantity', 1))
        expiry_minutes = getattr(settings, 'INVENTORY_RESERVATION_EXPIRY_MINUTES', 15)

        try:
            product.reserve_stock(quantity)
            reservation = StockReservation.objects.create(
                product=product,
                user=request.user,
                quantity=quantity,
                expires_at=timezone.now() + timedelta(minutes=expiry_minutes)
            )
            write_log(user=request.user, action='STOCK_RESERVED',
                      details=f"Reserved {quantity} of {product.product_id}, expires {reservation.expires_at}")
            return Response(StockReservationSerializer(reservation).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def release_expired(self, request):
        """Task 15: Release expired reservations"""
        expired = StockReservation.objects.filter(
            is_active=True,
            expires_at__lt=timezone.now()
        )
        released_count = 0
        for reservation in expired:
            reservation.release()
            released_count += 1
        return Response({'released_reservations': released_count})
