from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid
import os
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys
from django.core.validators import FileExtensionValidator


def user_profile_picture_path(instance, filename):
    """Generate upload path for user profile pictures: profiles/username_dob.ext"""
    ext = os.path.splitext(filename)[1]  # Get file extension
    dob_str = instance.date_of_birth.strftime('%Y%m%d') if instance.date_of_birth else 'nodob'
    new_filename = f"{instance.username}_{dob_str}{ext}"
    return os.path.join('profiles', new_filename)

class User(AbstractUser):
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    """
    Custom User model extending Django's AbstractUser.
    Supports student, teacher, and parent roles.
    """
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('teacher', 'Teacher'),
    )
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    
    # Required Profile Fields
    phone_number = models.CharField(max_length=15, blank=False, null=False, default='') # Now required
    date_of_birth = models.DateField(blank=False, null=False, default='2000-01-01') # Now required
    profile_picture = models.ImageField(
        upload_to=user_profile_picture_path, 
        blank=True, 
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])]
    )
    
    # Preferences
    preference_dark_mode = models.BooleanField(default=False)
    preference_email_notifications = models.BooleanField(default=True)
    
    # Student specific
    grade_level = models.CharField(max_length=20, blank=True, null=True)
    
    # Tracking fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_active = models.DateTimeField(auto_now=True)

    # NEXUS onboarding progress (0=not started, 1=academic, 2=syllabus, 3=confirmed)
    onboarding_step = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'users'
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if self.profile_picture:
            # Check if this is a new upload (InMemoryUploadedFile)
            if isinstance(self.profile_picture.file, InMemoryUploadedFile):
                try:
                    # Open image
                    img = Image.open(self.profile_picture.file)
                    
                    # Convert to RGB if needed
                    if img.mode in ('RGBA', 'P'):
                        img = img.convert('RGB')
                    
                    # Resize if too large (max 800x800)
                    max_size = (800, 800)
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                    
                    # Save to BytesIO
                    output = BytesIO()
                    img.save(output, format='JPEG', quality=80, optimize=True)
                    output.seek(0)
                    
                    # Update file content
                    # Change extension to .jpg
                    filename = os.path.splitext(self.profile_picture.name)[0]
                    new_filename = f"{filename}.jpg"
                    
                    self.profile_picture = InMemoryUploadedFile(
                        output,
                        'ImageField',
                        new_filename,
                        'image/jpeg',
                        sys.getsizeof(output),
                        None
                    )
                except Exception as e:
                    # Log error but don't stop save? Or fail?
                    # For now print to console
                    print(f"Error compressing image: {e}")
                    
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.username} ({self.role})"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username


import random
import string
from django.db.models.signals import pre_save
from django.dispatch import receiver

def generate_unique_code():
    length = 6
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        if not Classroom.objects.filter(access_code=code).exists():
            return code


class Classroom(models.Model):
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    name = models.CharField(max_length=100)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='teaching_classes')
    students = models.ManyToManyField(User, related_name='enrolled_classes', blank=True)
    co_teachers = models.ManyToManyField(User, related_name='co_teaching_classes', blank=True)
    access_code = models.CharField(max_length=6, unique=True, blank=True, null=True)
    is_join_by_code_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.is_join_by_code_enabled and not self.access_code:
            self.access_code = generate_unique_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class ClassroomInvitation(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    )
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='invitations')
    email = models.EmailField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('classroom', 'email')

    def __str__(self):
        return f"Invite for {self.email} to {self.classroom.name}"


class Notification(models.Model):
    """In-app notifications for users"""
    NOTIFICATION_TYPES = (
        ('quiz_assigned', 'Quiz Assigned'),
        ('quiz_graded', 'Quiz Graded'),
        ('classroom_invite', 'Classroom Invitation'),
        ('general', 'General'),
    )
    
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='general')
    is_read = models.BooleanField(default=False)
    
    # Generic reference to related object (quiz, session, link, etc.)
    related_object_id = models.CharField(max_length=36, null=True, blank=True)
    related_object_type = models.CharField(max_length=50, null=True, blank=True)  # 'quiz', 'session', 'link'
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"




class ClassroomLeaveRequest(models.Model):
    """Student request to leave a classroom, requiring teacher approval"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    )
    
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='leave_requests')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leave_requests')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    reason = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'classroom_leave_requests'
        unique_together = ('classroom', 'student', 'status') # Prevent multiple pending requests (needs careful handling)
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.username} wants to leave {self.classroom.name}"


# ==================== LEARNING DNA & PERSONALIZATION MODELS ====================

class LearningProfile(models.Model):
    """
    Student's Learning DNA profile created during onboarding.
    Stores learning preferences, initial ability, and behavioral patterns.
    """
    LEARNING_STYLE_CHOICES = (
        ('visual', 'Visual Learner'),
        ('reading', 'Reading/Writing Learner'),
        ('problem_solving', 'Problem-Solving Learner'),
        ('explanation', 'Explanation-Based Learner'),
    )
    
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='learning_profile')
    
    # Learning preferences
    learning_style = models.CharField(max_length=20, choices=LEARNING_STYLE_CHOICES, default='visual')
    preferred_study_time = models.CharField(max_length=20, blank=True, null=True)  # 'morning', 'afternoon', 'evening'
    
    # IRT-based ability estimation
    initial_ability = models.FloatField(default=0.0, help_text="Initial theta value from diagnostic test (IRT)")
    current_ability = models.FloatField(default=0.0, help_text="Current estimated ability (updated over time)")
    
    # Learning behavioral patterns
    learning_speed = models.FloatField(default=1.0, help_text="Relative learning speed (1.0 = average)")
    guessing_tendency = models.FloatField(default=0.0, help_text="Probability of guessing (0-1)")
    consistency_score = models.FloatField(default=0.5, help_text="Consistency in performance (0-1)")
    
    # Engagement metrics
    avg_session_duration = models.IntegerField(default=0, help_text="Average study session in minutes")
    total_study_time = models.IntegerField(default=0, help_text="Total study time in minutes")
    
    # Timestamps
    onboarding_completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'learning_profiles'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Learning Profile: {self.user.username} ({self.learning_style})"


class SubjectConfidence(models.Model):
    """
    Student's self-reported confidence level for each subject.
    Collected during onboarding and updated periodically.
    """
    SUBJECT_CHOICES = (
        ('mathematics', 'Mathematics'),
        ('science', 'Science'),
        ('english', 'English'),
        ('social_studies', 'Social Studies'),
        ('hindi', 'Hindi'),
        ('computer_science', 'Computer Science'),
    )
    
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    profile = models.ForeignKey(LearningProfile, on_delete=models.CASCADE, related_name='subject_confidences')
    subject = models.CharField(max_length=30, choices=SUBJECT_CHOICES)
    confidence_level = models.IntegerField(default=3, help_text="1=Very Low, 2=Low, 3=Medium, 4=High, 5=Very High")
    
    # Performance tracking
    actual_performance = models.FloatField(null=True, blank=True, help_text="Actual measured performance (0-1)")
    confidence_accuracy = models.FloatField(null=True, blank=True, help_text="How accurate is self-assessment")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'subject_confidences'
        unique_together = ('profile', 'subject')
        ordering = ['subject']
    
    def __str__(self):
        return f"{self.profile.user.username} - {self.subject}: {self.confidence_level}/5"


class MasteryVector(models.Model):
    """
    Tracks student's mastery level for each concept in the knowledge graph.
    Updated after each quiz/practice session.
    """
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mastery_vectors')
    concept_id = models.CharField(max_length=100, help_text="Reference to concept in knowledge graph")
    
    # Mastery metrics
    mastery_score = models.FloatField(default=0.0, help_text="Current mastery level (0-1)")
    attempts_count = models.IntegerField(default=0, help_text="Number of attempts on this concept")
    correct_count = models.IntegerField(default=0, help_text="Number of correct attempts")
    
    # Time tracking
    total_time_spent = models.IntegerField(default=0, help_text="Total time spent in seconds")
    last_practiced_at = models.DateTimeField(null=True, blank=True)
    
    # Learning trajectory
    initial_score = models.FloatField(default=0.0, help_text="First attempt score")
    peak_score = models.FloatField(default=0.0, help_text="Best score achieved")
    recent_trend = models.FloatField(default=0.0, help_text="Recent improvement trend (-1 to 1)")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'mastery_vectors'
        unique_together = ('user', 'concept_id')
        ordering = ['-mastery_score']
        indexes = [
            models.Index(fields=['user', 'mastery_score']),
            models.Index(fields=['concept_id']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.concept_id}: {self.mastery_score:.2f}"
    
    def update_mastery(self, is_correct, time_spent):
        """Update mastery score based on new attempt"""
        self.attempts_count += 1
        if is_correct:
            self.correct_count += 1
        
        self.total_time_spent += time_spent
        
        # Calculate new mastery score (weighted average with recency bias)
        accuracy = self.correct_count / self.attempts_count
        recency_weight = 0.3  # Give 30% weight to latest attempt
        self.mastery_score = (1 - recency_weight) * self.mastery_score + recency_weight * (1.0 if is_correct else 0.0)
        
        # Update peak score
        if self.mastery_score > self.peak_score:
            self.peak_score = self.mastery_score
        
        self.last_practiced_at = models.functions.Now()
        self.save()


# ==================== CLASSROOM QUIZ MANAGEMENT ====================

class ClassroomQuizAssignment(models.Model):
    """Links quizzes to classrooms with assignment-specific settings"""
    QUIZ_MODE_CHOICES = (
        ('practice', 'Practice'),
        ('assessment', 'Assessment'),
    )
    
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='assigned_quizzes')
    quiz = models.ForeignKey('quiz.Quiz', on_delete=models.CASCADE, related_name='classroom_assignments')
    
    # Assignment metadata
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assigned_quizzes')
    assigned_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(null=True, blank=True)
    
    # Quiz mode and settings
    quiz_mode = models.CharField(max_length=20, choices=QUIZ_MODE_CHOICES, default='practice')
    
    # Practice mode settings
    allow_unlimited_attempts = models.BooleanField(default=True, help_text="For practice mode")
    show_immediate_feedback = models.BooleanField(default=True, help_text="For practice mode")
    
    # Assessment mode settings  
    max_attempts = models.IntegerField(default=1, help_text="For assessment mode")
    strict_time_limit = models.BooleanField(default=True, help_text="Enforce time limit strictly")
    enable_proctoring = models.BooleanField(default=False, help_text="Enable proctoring features")
    shuffle_questions = models.BooleanField(default=True, help_text="Randomize question order for students")
    shuffle_options = models.BooleanField(default=True, help_text="Randomize answer options for students")
    show_results_after_due = models.BooleanField(default=True, help_text="Show results only after due date")
    
    # Gating: Prerequisite Learning Module
    prerequisite_module = models.ForeignKey(
        'learning.LearningModule', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='dependent_quizzes',
        help_text="Student must complete this module before taking the quiz"
    )
    time_limit_minutes = models.IntegerField(null=True, blank=True, help_text="Time limit for this assignment")
    
    # Status
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'classroom_quiz_assignments'
        unique_together = ('classroom', 'quiz')
        ordering = ['-assigned_at']
    
    def __str__(self):
        return f"{self.quiz.title} → {self.classroom.name} ({self.quiz_mode})"


class Achievement(models.Model):
    """Student milestones and badges"""
    ACHIEVEMENT_TYPES = (
        ('diagnostic_complete', 'AI Diagnostic Pioneer'),
        ('perfect_score', 'Perfect Scorer'),
        ('consistent_learner', 'Consistency Master'),
        ('top_performer', 'Top Performer'),
    )

    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements')
    achievement_type = models.CharField(max_length=50, choices=ACHIEVEMENT_TYPES)
    title = models.CharField(max_length=100)
    description = models.TextField()
    icon_type = models.CharField(max_length=50, default='award') # Lucide icon name
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'achievements'
        ordering = ['-earned_at']
        unique_together = ('user', 'achievement_type')

    def __str__(self):
        return f"{self.user.username} - {self.title}"


# ==================== NEXUS ACADEMIC PROFILE ====================

class AcademicProfile(models.Model):
    """
    NEXUS onboarding: stores a student's academic context.
    Created during /nexus/onboarding/academic step.
    """
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='academic_profile')

    # Academic details
    institution = models.CharField(max_length=200, blank=True, default='')
    department = models.CharField(max_length=100)
    semester = models.CharField(max_length=20)         # e.g. "Semester 3", "Year 2"
    academic_year = models.CharField(max_length=20)    # e.g. "2025-26"

    # Goals & schedule
    career_goal = models.CharField(max_length=200, blank=True, default='')
    study_hours_per_day = models.FloatField(default=2.0)

    # Onboarding completion flag
    onboarding_completed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'nexus_academic_profiles'

    def __str__(self):
        return f"{self.user.username} — {self.department}, {self.semester}"
