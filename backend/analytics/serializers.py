from rest_framework import serializers
from .models import Analytics


class AnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for Analytics model"""
    user_name = serializers.CharField(source='user.username', read_only=True)
    session_id = serializers.IntegerField(source='session.id', read_only=True, allow_null=True)
    
    class Meta:
        model = Analytics
        fields = ('id', 'user', 'user_name', 'session', 'session_id',
                  'weak_topics', 'strong_topics', 'predicted_weak_topics',
                  'mindset', 'learning_strategy', 'performance_trend',
                  'avg_study_time', 'consistency_score', 'engagement_level',
                  'mastered_subtopics', 'recommended_learning_path',
                  'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at')


class DashboardDataSerializer(serializers.Serializer):
    """Serializer for dashboard data aggregation"""
    user_id = serializers.IntegerField()
    user_name = serializers.CharField()
    total_quizzes = serializers.IntegerField()
    total_questions_answered = serializers.IntegerField()
    overall_accuracy = serializers.FloatField()
    avg_score = serializers.FloatField()
    current_mindset = serializers.CharField()
    weak_topics = serializers.ListField()
    strong_topics = serializers.ListField()
    predicted_weak_topics = serializers.ListField()
    learning_strategy = serializers.DictField()
    performance_trend = serializers.ListField()
    recommended_learning_path = serializers.ListField()


class WeakTopicPredictionSerializer(serializers.Serializer):
    """Serializer for weak topic predictions"""
    topic_id = serializers.IntegerField()
    topic_name = serializers.CharField()
    weakness_probability = serializers.FloatField()
    is_weak = serializers.BooleanField()


class LearningStrategySerializer(serializers.Serializer):
    """Serializer for personalized learning strategy"""
    strategy_type = serializers.CharField()
    recommended_actions = serializers.ListField()
    focus_areas = serializers.ListField()
    estimated_study_time = serializers.IntegerField()
    difficulty_adjustment = serializers.CharField()
