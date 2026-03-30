from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import serializers

from .models import Event, EventStatus
from .utils import dispatch_event


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['id', 'sequence', 'event_type', 'payload', 'status',
                  'error_message', 'created_at', 'processed_at']


class EventViewSet(viewsets.ReadOnlyModelViewSet):
    """Task 14: Event-Driven System"""
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    filterset_fields = ['event_type', 'status']
    ordering_fields = ['sequence', 'created_at']

    @action(detail=False, methods=['post'], url_path='dispatch')
    def dispatch_test(self, request):
        """Manually dispatch a test event"""
        event_type = request.data.get('event_type', 'ORDER_CREATED')
        payload = request.data.get('payload', {})
        event = dispatch_event(event_type, payload)
        if event:
            return Response(EventSerializer(event).data, status=status.HTTP_201_CREATED)
        return Response({'error': 'Failed to dispatch event'}, status=400)

    @action(detail=False, methods=['get'], url_path='pending')
    def pending_events(self, request):
        """View pending/failed events"""
        events = Event.objects.filter(status__in=[EventStatus.PENDING, EventStatus.FAILED])
        return Response(EventSerializer(events, many=True).data)
