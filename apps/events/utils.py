def dispatch_event(event_type, payload=None):
    """
    Task 14: Dispatch an event to the event queue.
    Safe to call from anywhere — fails silently if DB is unavailable.
    """
    try:
        from .models import Event
        last = Event.objects.order_by('-sequence').first()
        next_seq = (last.sequence + 1) if last else 1
        event = Event.objects.create(
            event_type=event_type,
            payload=payload or {},
            sequence=next_seq,
        )
        # Auto-process the event inline (simulated queue)
        _process_event(event)
        return event
    except Exception:
        pass


def _process_event(event):
    """Simulate event handler execution in order"""
    from django.utils import timezone
    try:
        # Task 14: Events must execute in order — check no prior PENDING events
        from .models import Event, EventStatus
        pending_before = Event.objects.filter(
            sequence__lt=event.sequence,
            status=EventStatus.PENDING
        ).exists()

        if pending_before:
            event.error_message = "Blocked: earlier event still pending"
            event.status = EventStatus.FAILED
            event.save(update_fields=['status', 'error_message'])
            return

        # Mark as processed
        event.status = EventStatus.PROCESSED
        event.processed_at = timezone.now()
        event.save(update_fields=['status', 'processed_at'])

    except Exception as e:
        event.status = 'FAILED'
        event.error_message = str(e)
        event.save(update_fields=['status', 'error_message'])
