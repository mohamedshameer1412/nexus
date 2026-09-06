"""
nexus_core/serializers.py
Serializes the LearnerDigitalTwin and AgentDecisionLog for API responses.
"""
from rest_framework import serializers
from .models import LearnerDigitalTwin, AgentDecisionLog


class DigitalTwinSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = LearnerDigitalTwin
        fields = [
            "id", "username", "email",
            "verified_mastery", "self_reported_mastery", "confidence_gap",
            "learning_debt_score", "failure_risk_score", "concept_drift_score",
            "career_goal", "target_exam_score",
            "verified_skills", "retention_scores",
            "last_updated", "created_at",
        ]
        read_only_fields = [
            "id", "username", "email",
            "verified_mastery", "confidence_gap",
            "learning_debt_score", "failure_risk_score", "concept_drift_score",
            "verified_skills", "retention_scores",
            "last_updated", "created_at",
        ]


class SelfMasteryUpdateSerializer(serializers.Serializer):
    """
    Accepts student-reported perceived mastery per topic.
    {topic_id: perceived_pct, ...}
    """
    self_reported_mastery = serializers.DictField(
        child=serializers.FloatField(min_value=0, max_value=100)
    )
    career_goal = serializers.CharField(max_length=200, required=False, allow_blank=True)
    target_exam_score = serializers.FloatField(min_value=0, max_value=100, required=False)


class AgentDecisionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentDecisionLog
        fields = [
            "id", "agent_name", "trigger",
            "input_state", "decision", "output",
            "verified", "timestamp",
        ]
        read_only_fields = fields
