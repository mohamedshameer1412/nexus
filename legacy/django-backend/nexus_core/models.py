import uuid
from django.db import models
from django.conf import settings


class LearnerDigitalTwin(models.Model):
    """
    The central shared state object for NEXUS.
    All 6 agents read from and write to this object.
    Updated after every assessment, tutor session, and intervention.
    """
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='digital_twin')

    # Aggregated mastery state (across ALL subjects)
    verified_mastery = models.JSONField(default=dict)       # {topic_id: pct}
    self_reported_mastery = models.JSONField(default=dict)  # {topic_id: pct}
    confidence_gap = models.JSONField(default=dict)         # {topic_id: gap}

    # Risk + debt metrics
    learning_debt_score = models.FloatField(default=0.0)    # 0–100 overall debt
    failure_risk_score = models.FloatField(default=0.0)     # 0–100 exam failure risk
    concept_drift_score = models.FloatField(default=0.0)    # how much has been forgotten

    # Goals
    career_goal = models.CharField(max_length=200, blank=True, default='')
    target_exam_score = models.FloatField(default=75.0)

    # Verified skills (claimed + evidence-backed)
    verified_skills = models.JSONField(default=dict)        # {skill: {level, evidence_pct}}

    # Retention tracking
    retention_scores = models.JSONField(default=dict)       # {topic_id: retention_pct}

    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'nexus_digital_twins'

    def __str__(self):
        return f"Digital Twin: {self.user.username} (debt={self.learning_debt_score:.0f}, risk={self.failure_risk_score:.0f})"


class AgentDecisionLog(models.Model):
    """
    Every decision made by any agent is logged here for full transparency.
    This powers the 'Why did NEXUS choose this?' view.
    """
    AGENT_CHOICES = [
        ('analytics', 'Analytics Agent'),
        ('evaluator', 'Evaluator Agent'),
        ('planner', 'Planner Agent'),
        ('content', 'Content Agent'),
        ('tutor', 'Tutor Agent'),
        ('mentor', 'Mentor Agent'),
    ]

    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='agent_logs')
    twin = models.ForeignKey(LearnerDigitalTwin, on_delete=models.CASCADE,
                             related_name='decision_logs')

    agent_name = models.CharField(max_length=20, choices=AGENT_CHOICES)
    trigger = models.CharField(max_length=100, blank=True)   # what caused this decision
    input_state = models.JSONField(default=dict)              # snapshot of relevant state
    decision = models.TextField()                              # what was decided (human-readable)
    output = models.JSONField(default=dict)                    # structured output
    verified = models.BooleanField(null=True)                  # did the intervention work?

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'nexus_agent_decision_logs'
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.agent_name}] {self.user.username}: {self.decision[:80]}"
