import uuid
from django.db import models
from django.conf import settings


class TutorSession(models.Model):
    """One session per student per topic learning interaction."""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('abandoned', 'Abandoned'),
    ]

    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='tutor_sessions')
    subject = models.ForeignKey('syllabus.AcademicSubject', on_delete=models.CASCADE,
                                related_name='tutor_sessions')
    unit_name = models.CharField(max_length=200)
    topic_name = models.CharField(max_length=200)

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='active')

    # Context used by Gemini (serialized file excerpts for this topic)
    context_summary = models.TextField(blank=True, default='')

    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'nexus_tutor_sessions'
        ordering = ['-started_at']

    def __str__(self):
        return f"Tutor: {self.user.username} — {self.topic_name} ({self.status})"


class TutorMessage(models.Model):
    """Individual message in a tutor session chat."""
    ROLE_CHOICES = [('user', 'User'), ('assistant', 'Assistant')]

    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    session = models.ForeignKey(TutorSession, on_delete=models.CASCADE,
                                related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'nexus_tutor_messages'
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.role}] {self.content[:60]}"
