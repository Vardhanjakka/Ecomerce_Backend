from django.db import models
from django.contrib.auth.models import User


class AuditLog(models.Model):
    """
    Task 16: Audit Logging System
    Immutable logs - no update/delete allowed
    Format: [Time] USER_1 added PRODUCT_2 qty=3
    """
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    username_snapshot = models.CharField(max_length=150)  # preserve even if user deleted
    action = models.CharField(max_length=100, db_index=True)
    details = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        # Task 16: Immutable — no permissions to update/delete in API

    def __str__(self):
        return f"[{self.created_at}] {self.username_snapshot} {self.action}: {self.details[:80]}"

    def save(self, *args, **kwargs):
        # Task 16: Immutable — only allow insert, never update
        if self.pk:
            raise PermissionError("AuditLog entries are immutable and cannot be modified.")
        if self.user and not self.username_snapshot:
            self.username_snapshot = self.user.username
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("AuditLog entries cannot be deleted.")
