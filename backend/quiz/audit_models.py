from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class QuizResetLog(models.Model):
    """Audit log for quiz attempt resets"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='reset_actions')
    target_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reset_received')
    quiz = models.ForeignKey('quiz.Quiz', on_delete=models.SET_NULL, null=True, blank=True)
    reset_type = models.CharField(max_length=50, choices=[
        ('specific', 'Specific User + Quiz'),
        ('all_students_one_quiz', 'All Students for One Quiz'),
        ('one_student_all_quizzes', 'One Student for All Quizzes'),
        ('all_students_all_quizzes', 'All Students for All Quizzes'),
    ])
    sessions_deleted = models.IntegerField(default=0)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'quiz_reset_logs'
        ordering = ['-created_at']
        app_label = 'quiz'
    
    def __str__(self):
        return f"{self.teacher.email if self.teacher else 'Unknown'} reset {self.sessions_deleted} sessions"
