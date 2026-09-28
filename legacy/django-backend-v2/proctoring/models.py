from django.db import models
from quiz.models import QuizSession

class ProctoringEvent(models.Model):
    EVENT_TYPES = (
        ('tab_switch', 'Tab Switch'),
        ('face_not_visible', 'Face Not Visible'),
        ('multiple_faces', 'Multiple Faces Detected'),
        ('looking_away', 'Looking Away'),
        ('speech_detected', 'Speech Detected'),
        ('screen_sharing', 'Screen Sharing Detected'),
        ('browser_resize', 'Browser Resized'),
        ('full_screen_exit', 'Exited Full Screen'),
        ('auto_submit', 'Auto Submission Triggered'),
        ('copy_attempt', 'Clipboard Copy Attempt'),
        ('paste_attempt', 'Clipboard Paste Attempt'),
    )
    
    session = models.ForeignKey(QuizSession, on_delete=models.CASCADE, related_name='proctoring_events')
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(default=dict)  # e.g. {'duration': 5, 'confidence': 0.9}
    evidence_image = models.ImageField(upload_to='proctoring_evidence/', null=True, blank=True)
    
    # Severity score for this specific event (0-100)
    # 0 = info, 100 = implementation of cheating
    severity_score = models.IntegerField(default=0)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.event_type} - {self.session.user.username} ({self.timestamp})"

    def save(self, *args, **kwargs):
        # Auto-calculate severity if not set
        if self.severity_score == 0:
            if self.event_type in ['multiple_faces', 'screen_sharing']:
                self.severity_score = 100
            elif self.event_type == 'tab_switch':
                self.severity_score = 60
            elif self.event_type in ['face_not_visible', 'looking_away']:
                self.severity_score = 40
            elif self.event_type in ['browser_resize', 'full_screen_exit']:
                self.severity_score = 30
        super().save(*args, **kwargs)
