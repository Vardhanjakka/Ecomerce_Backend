def write_log(user, action, details, ip_address=None):
    """
    Task 16: Central logging utility.
    Called from every significant action across all apps.
    """
    try:
        from .models import AuditLog
        username = user.username if user and hasattr(user, 'username') else 'system'
        AuditLog.objects.create(
            user=user if (user and hasattr(user, 'pk') and user.pk) else None,
            username_snapshot=username,
            action=action,
            details=details,
            ip_address=ip_address,
        )
    except Exception:
        pass  # Never let logging break the main flow
