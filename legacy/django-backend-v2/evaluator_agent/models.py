import uuid
from django.db import models
from django.conf import settings


class TopicMastery(models.Model):
    """
    The KEY state record. Tracks verified vs self-reported mastery per topic.
    Created automatically when a roadmap is confirmed.
    """
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('weak', 'Weak (< 50%)'),
        ('developing', 'Developing (50–79%)'),
        ('mastered', 'Mastered (≥ 80%)'),
    ]

    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='topic_masteries')
    subject = models.ForeignKey('syllabus.AcademicSubject', on_delete=models.CASCADE,
                                related_name='topic_masteries')

    unit_name = models.CharField(max_length=200)
    topic_name = models.CharField(max_length=200)
    subtopics = models.JSONField(default=list)
    lab_exercises = models.JSONField(default=list)

    # The critical split: self-claimed vs evidence-backed
    self_reported_pct = models.FloatField(default=0.0)    # What student claims
    verified_pct = models.FloatField(default=0.0)          # What evidence shows
    confidence_gap = models.FloatField(default=0.0)        # self - verified

    # Trend
    mastery_trend = models.FloatField(default=0.0)         # positive = improving
    attempts_count = models.IntegerField(default=0)
    last_assessed_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='not_started')

    # Failure risk (computed by Analytics agent)
    failure_risk_pct = models.FloatField(default=0.0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'nexus_topic_masteries'
        unique_together = ('user', 'subject', 'unit_name', 'topic_name')
        ordering = ['unit_name', 'topic_name']

    def __str__(self):
        return f"{self.user.username} — {self.topic_name}: {self.verified_pct:.0f}% verified"

    def update_status(self):
        """Recalculate status from verified_pct."""
        if self.verified_pct == 0 and self.attempts_count == 0:
            self.status = 'not_started'
        elif self.verified_pct < 50:
            self.status = 'weak'
        elif self.verified_pct < 80:
            self.status = 'developing'
        else:
            self.status = 'mastered'
        self.confidence_gap = round(self.self_reported_pct - self.verified_pct, 1)


class DiagnosticSession(models.Model):
    """One assessment session — captures score, timing, errors, root cause."""
    SESSION_TYPE_CHOICES = [
        ('diagnostic', 'Initial Diagnostic'),
        ('verification', 'Post-Intervention Verification'),
        ('pyq_practice', 'PYQ Practice'),
    ]

    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='diagnostic_sessions')
    topic_mastery = models.ForeignKey(TopicMastery, on_delete=models.CASCADE,
                                      related_name='sessions')

    session_type = models.CharField(max_length=20, choices=SESSION_TYPE_CHOICES,
                                    default='diagnostic')
    status = models.CharField(max_length=15,
                              choices=[('active','Active'),('completed','Completed'),
                                       ('terminated','Terminated')],
                              default='active')

    score_pct = models.FloatField(default=0.0)
    questions_attempted = models.IntegerField(default=0)
    questions_correct = models.IntegerField(default=0)
    time_taken_seconds = models.IntegerField(default=0)

    # Error analysis
    error_categories = models.JSONField(default=dict)   # {conceptual: 2, application: 1}

    # AI-generated root cause (Gemini analysis after session)
    root_cause_analysis = models.TextField(blank=True, default='')
    weak_subtopics = models.JSONField(default=list)

    # Integrity signals
    tab_switches = models.IntegerField(default=0)
    integrity_terminated = models.BooleanField(default=False)

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'nexus_diagnostic_sessions'
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.user.username} — {self.topic_mastery.topic_name} ({self.score_pct:.0f}%)"


class DiagnosticQuestion(models.Model):
    """Individual question within a diagnostic session."""
    DIFFICULTY_CHOICES = [(i, str(i)) for i in range(1, 6)]

    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    session = models.ForeignKey(DiagnosticSession, on_delete=models.CASCADE,
                                related_name='questions')

    question_text = models.TextField()
    options = models.JSONField(default=list)          # [{"key":"A","text":"..."}]
    correct_answer = models.CharField(max_length=5)   # "A", "B", "C", "D"
    explanation = models.TextField(blank=True, default='')

    student_answer = models.CharField(max_length=5, blank=True, default='')
    is_correct = models.BooleanField(null=True)
    time_taken_seconds = models.IntegerField(default=0)

    difficulty_level = models.IntegerField(choices=DIFFICULTY_CHOICES, default=3)
    concept_tag = models.CharField(max_length=100, blank=True, default='')
    question_type = models.CharField(max_length=30, default='mcq')  # mcq, true_false, trace

    order_in_session = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'nexus_diagnostic_questions'
        ordering = ['order_in_session']

    def __str__(self):
        status = "✓" if self.is_correct else "✗" if self.is_correct is False else "?"
        return f"Q{self.order_in_session} [{status}] {self.question_text[:60]}"
