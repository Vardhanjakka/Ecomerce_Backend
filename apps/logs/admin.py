from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'username_snapshot', 'action', 'details']
    list_filter = ['action']
    search_fields = ['username_snapshot', 'action', 'details']
    readonly_fields = ['user', 'username_snapshot', 'action', 'details', 'ip_address', 'created_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
