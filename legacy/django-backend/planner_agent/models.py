import uuid
from django.db import models
from django.conf import settings


class LearningDebt(models.Model):
    """
    Learning Debt record — identifies a bottleneck topic that is blocking
    multiple downstream topics. The higher the debt_score, the more urgent
    it is to fix this concept.
    """
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='learning_debts')
    subject = models.ForeignKey('syllabus.AcademicSubject', on_delete=models.CASCADE,
                                related_name='learning_debts')

    root_concept = models.CharField(max_length=200)     # The bottleneck topic name
    root_topic_mastery = models.ForeignKey(
        'evaluator_agent.TopicMastery',
        on_delete=models.CASCADE,
        related_name='debt_as_root',
        null=True, blank=True
    )

    debt_score = models.FloatField(default=0.0)          # 0–100, higher = more urgent
    affected_topics = models.JSONField(default=list)     # ["Trees", "Graphs", "Heaps"]
    persistence_days = models.IntegerField(default=0)    # How long this has been unresolved

    last_calculated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'nexus_learning_debts'
        ordering = ['-debt_score']

    def __str__(self):
        return f"Debt: {self.root_concept} ({self.debt_score:.0f}/100) → {len(self.affected_topics)} topics"


class StudyPlan(models.Model):
    """
    AI-generated study plan for a user for a specific subject.
    plan_json: [{"duration_min": 20, "action": "teach", "topic": "Recursion", "reason": "..."}]
    """
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='study_plans')
    subject = models.ForeignKey('syllabus.AcademicSubject', on_delete=models.CASCADE,
                                related_name='study_plans')

    plan_json = models.JSONField(default=list)
    total_duration_min = models.IntegerField(default=0)
    exam_deadline = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    # What triggered this plan
    trigger = models.CharField(max_length=50, default='manual')  # manual, post_assessment, scheduled

    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'nexus_study_plans'
        ordering = ['-generated_at']

    def __str__(self):
        return f"Plan: {self.user.username} — {self.subject.name} ({self.total_duration_min}min)"
