from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()

class LearningModule(models.Model):
    """
    Represents a learning unit (PDF, Video, etc.) linked to a classroom.
    Prerequisite for taking certain quizzes.
    """
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Content Source
    pdf_file = models.FileField(upload_to='learning_modules/pdfs/', null=True, blank=True)
    content_text = models.TextField(blank=True, help_text="Extracted text from PDF for AI processing")
    
    # Metadata
    classroom = models.ForeignKey('users.Classroom', on_delete=models.CASCADE, related_name='learning_modules')
    topic = models.ForeignKey('quiz.Topic', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Workflow
    is_published = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_modules')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'learning_modules'
        ordering = ['-created_at']
        
    def __str__(self):
        return self.title

class FlashcardDeck(models.Model):
    """Collection of flashcards generated from a module"""
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    module = models.ForeignKey(LearningModule, on_delete=models.CASCADE, related_name='flashcard_decks')
    name = models.CharField(max_length=200)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'flashcard_decks'
        
    def __str__(self):
        return self.name

class Flashcard(models.Model):
    """Individual flashcard"""
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    deck = models.ForeignKey(FlashcardDeck, on_delete=models.CASCADE, related_name='cards')
    front = models.TextField()
    back = models.TextField()
    
    # AI Metadata
    is_ai_generated = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'flashcards'

class StudentModuleProgress(models.Model):
    """Tracks student progress through a learning module"""
    STATUS_CHOICES = (
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    )
    
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='module_progress')
    module = models.ForeignKey(LearningModule, on_delete=models.CASCADE, related_name='student_progress')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    
    # Metrics
    time_spent_seconds = models.IntegerField(default=0)
    last_accessed_at = models.DateTimeField(auto_now=True)
    completion_percentage = models.FloatField(default=0.0)
    
    # Specific component tracking
    flashcards_studied_count = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'student_module_progress'
        unique_together = ['student', 'module']
