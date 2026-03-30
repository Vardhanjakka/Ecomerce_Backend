from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import serializers
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = ['id', 'username_snapshot', 'action', 'details', 'ip_address', 'created_at']
        read_only_fields = fields


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Task 16: Audit Logging System — read-only, immutable logs
    Format: [Time] USER action: details
    """
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['username_snapshot', 'action', 'details']
    ordering_fields = ['created_at', 'action']

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return AuditLog.objects.all()
        return AuditLog.objects.filter(user=user)
