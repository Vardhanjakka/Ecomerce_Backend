from django.contrib import admin
from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['sequence', 'event_type', 'status', 'created_at', 'processed_at']
    list_filter = ['event_type', 'status']
    readonly_fields = ['sequence', 'created_at', 'processed_at']
