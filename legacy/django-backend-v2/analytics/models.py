from django.db import models
import uuid


class Analytics(models.Model):
    """Analytics and performance tracking for students"""
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='analytics')
    session = models.OneToOneField('quiz.QuizSession', on_delete=models.CASCADE, related_name='analytics', null=True, blank=True)
    
    # Topic performance
    weak_topics = models.JSONField(default=list, help_text="List of weak topics with scores")
    strong_topics = models.JSONField(default=list, help_text="List of strong topics with scores")
    predicted_weak_topics = models.JSONField(default=list, help_text="ML predicted weak topics")
    
    # Learning insights
    mindset = models.CharField(max_length=20, default='neutral')
    learning_strategy = models.JSONField(default=dict, help_text="Personalized learning recommendations")
    performance_trend = models.JSONField(default=list, help_text="Historical performance data")
    
    # Engagement metrics
    avg_study_time = models.FloatField(default=0.0, help_text="Average study time in minutes")
    consistency_score = models.FloatField(default=0.0, help_text="Consistency score (0-100)")
    engagement_level = models.CharField(max_length=20, default='neutral')
    
    # Knowledge graph data
    mastered_subtopics = models.JSONField(default=list)
    recommended_learning_path = models.JSONField(default=list)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'analytics'
        ordering = ['-updated_at']
        verbose_name_plural = 'Analytics'
    
    def __str__(self):
        return f"Analytics for {self.user.username}"
