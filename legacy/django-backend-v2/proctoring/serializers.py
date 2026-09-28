from rest_framework import serializers
from .models import ProctoringEvent

class ProctoringEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProctoringEvent
        fields = ['id', 'session', 'event_type', 'timestamp', 'details', 'evidence_image', 'severity_score']
        read_only_fields = ['id', 'timestamp', 'severity_score']

class ProctoringReportSerializer(serializers.Serializer):
    trust_score = serializers.IntegerField()
    total_events = serializers.IntegerField()
    event_counts = serializers.DictField()
    events = ProctoringEventSerializer(many=True)
