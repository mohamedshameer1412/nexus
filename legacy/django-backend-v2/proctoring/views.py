from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import ProctoringEvent
from .serializers import ProctoringEventSerializer, ProctoringReportSerializer
from quiz.models import QuizSession

class ProctoringViewSet(viewsets.ModelViewSet):
    queryset = ProctoringEvent.objects.all()
    serializer_class = ProctoringEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'student':
            # Students can create logs for their sessions via POST, but listing should be restricted
            # Usually students don't need to list events.
            # But the viewset validation allows Create.
            return ProctoringEvent.objects.filter(session__user=user)
        elif user.role == 'teacher':
             # Teachers can see events for sessions in their classrooms
             return ProctoringEvent.objects.filter(session__quiz__created_by=user)
        return ProctoringEvent.objects.none()

    def perform_create(self, serializer):
        # Validate that the user owns the session
        session = serializer.validated_data['session']
        if session.user != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only log events for your own session.")
        serializer.save()

    @action(detail=False, methods=['get'], url_path='sessions/(?P<session_id>[^/.]+)/report')
    def session_report(self, request, session_id=None):
        """Generate a proctoring report for a specific session"""
        try:
            session = QuizSession.objects.get(id=session_id)
        except QuizSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)

        # Check permission: Teacher of quiz or Admin
        if request.user != session.quiz.created_by and not request.user.is_staff:
             return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        events = ProctoringEvent.objects.filter(session=session).order_by('timestamp')
        total_events = events.count()
        
        # Calculate Trust Score
        # Start with 100
        # Deduct severity scores
        total_severity = sum(e.severity_score for e in events)
        trust_score = max(0, 100 - total_severity)
        
        # Breakdown
        event_counts = {}
        for e in events:
            event_counts[e.event_type] = event_counts.get(e.event_type, 0) + 1
            
        report_data = {
            'trust_score': trust_score,
            'total_events': total_events,
            'event_counts': event_counts,
            'events': events
        }
        
        serializer = ProctoringReportSerializer(report_data)
        return Response(serializer.data)
