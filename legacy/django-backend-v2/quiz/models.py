from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator, MinLengthValidator, MaxLengthValidator
from django.core.exceptions import ValidationError
import uuid

User = get_user_model()


class Topic(models.Model):
    """Main topic/subject category"""
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_topics')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'topics'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Subtopic(models.Model):
    """Subtopic within a main topic"""
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='subtopics')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    prerequisite_subtopics = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='dependent_subtopics')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'subtopics'
        ordering = ['topic', 'name']
        unique_together = ['topic', 'name']
    
    def __str__(self):
        return f"{self.topic.name} - {self.name}"


class Question(models.Model):
    """Quiz question with IRT parameters"""
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    
    # Question Type - NEW
    QUESTION_TYPE_CHOICES = [
        ('mcq', 'Multiple Choice'),
    ]
    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPE_CHOICES,
        default='mcq',
        help_text="Type of question"
    )
    
    DIFFICULTY_CHOICES = (
        (1, 'Very Easy'),
        (2, 'Easy'),
        (3, 'Medium'),
        (4, 'Hard'),
        (5, 'Very Hard'),
    )
    
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='questions')
    subtopic = models.ForeignKey(Subtopic, on_delete=models.CASCADE, related_name='questions', null=True, blank=True)
    learning_module = models.ForeignKey(
        'learning.LearningModule', 
        on_delete=models.CASCADE, 
        related_name='questions', 
        null=True, 
        blank=True,
        help_text="The learning module this question was generated from"
    )
    question_text = models.TextField(validators=[MinLengthValidator(10, "Question must be at least 10 characters"), MaxLengthValidator(1000, "Question must not exceed 1000 characters")])
    
    # Image for question (optional)
    image = models.ImageField(upload_to='question_images/', null=True, blank=True, help_text="Optional image for the question")
    
    # Multiple choice options (for MCQ type)
    option_a = models.CharField(max_length=500, blank=True, validators=[MinLengthValidator(1, "Option cannot be empty")])
    option_b = models.CharField(max_length=500, blank=True, validators=[MinLengthValidator(1, "Option cannot be empty")])
    option_c = models.CharField(max_length=500, blank=True, validators=[MinLengthValidator(1, "Option cannot be empty")])
    option_d = models.CharField(max_length=500, blank=True, validators=[MinLengthValidator(1, "Option cannot be empty")])
    correct_answer = models.CharField(max_length=1, choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')], blank=True)
    
    
    # Difficulty and IRT parameters
    difficulty_level = models.IntegerField(choices=DIFFICULTY_CHOICES, default=3, validators=[MinValueValidator(1), MaxValueValidator(5)])
    irt_difficulty = models.FloatField(default=0.0, help_text="IRT difficulty parameter (b)")
    irt_discrimination = models.FloatField(default=1.0, help_text="IRT discrimination parameter (a)")
    
    # Metadata
    explanation = models.TextField(blank=True, help_text="Explanation for the correct answer")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Statistics
    times_asked = models.IntegerField(default=0)
    times_correct = models.IntegerField(default=0)
    is_approved = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'questions'
        ordering = ['-created_at']
    
    def __str__(self):
        topic_name = self.topic.name if self.topic else "No Topic"
        return f"{topic_name} - Q{self.id}"
    
    @property
    def success_rate(self):
        if self.times_asked == 0:
            return 0
        return (self.times_correct / self.times_asked) * 100
    
    def clean(self):
        """Validate question data"""
        super().clean()
        
        if self.question_type == 'mcq':
            # Check for duplicate options
            options = [self.option_a, self.option_b, self.option_c, self.option_d]
            # Filter out empty options just in case, though validators should catch them
            options = [opt for opt in options if opt]
            if len(options) != len(set(options)):
                raise ValidationError("All options must be unique")
            
            # Validate correct answer
            if self.correct_answer not in ['A', 'B', 'C', 'D']:
                raise ValidationError("Correct answer must be A, B, C, or D for MCQ")
        
        elif self.question_type in ['short_answer', 'essay']:
            # For text questions, we require model_answer? Not strictly enforced by DB constraint but good for logic.
            # self.model_answer logic is optional depending on business rule, leaving relaxed for now.
            pass


class Quiz(models.Model):
    """Quiz configuration"""
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    title = models.CharField(max_length=200, validators=[MinLengthValidator(3, "Title must be at least 3 characters")])
    description = models.TextField(blank=True)
    topics = models.ManyToManyField(Topic, related_name='quizzes')
    total_questions = models.IntegerField(default=10, validators=[MinValueValidator(1, "Must have at least 1 question"), MaxValueValidator(100, "Cannot exceed 100 questions")])
    time_limit = models.IntegerField(help_text="Time limit in minutes", null=True, blank=True, validators=[MinValueValidator(1, "Time limit must be at least 1 minute"), MaxValueValidator(1440, "Time limit cannot exceed 24 hours")])
    is_adaptive = models.BooleanField(default=True, help_text="Enable adaptive difficulty")
    is_active = models.BooleanField(default=True, help_text="Is this quiz active")
    
    # Question Type Configuration
    QUESTION_TYPE_CHOICES = [
        ('mixed', 'Mixed / All Types'),
        ('mcq', 'Multiple Choice'),
    ]
    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPE_CHOICES,
        default='mixed',
        help_text="Type of questions in this quiz"
    )
    
    # Global Quiz Settings (for overall dashboard access)
    allow_retakes = models.BooleanField(default=False, help_text="Allow students to retake this quiz (global)")
    max_attempts = models.IntegerField(
        default=1, 
        help_text="Maximum attempts for global access", 
        validators=[MinValueValidator(1, "Must allow at least 1 attempt"), MaxValueValidator(100, "Cannot exceed 100 attempts")]
    )
    show_answers = models.BooleanField(default=False, help_text="Show correct answers after completion")
    show_explanations = models.BooleanField(default=True, help_text="Show explanations for answers")
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_quizzes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'quizzes'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def clean(self):
        """Validate quiz configuration"""
        super().clean()
        
        # Validate max_attempts when retakes are allowed
        if self.allow_retakes and self.max_attempts < 1:
            raise ValidationError("Max attempts must be at least 1 when retakes are allowed")
        
        # Validate time_limit if set
        if self.time_limit is not None and self.time_limit <= 0:
            raise ValidationError("Time limit must be greater than 0 if set")


class QuizSession(models.Model):
    """Individual quiz attempt by a user"""
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    MINDSET_CHOICES = (
        ('confident', 'Confident'),
        ('confused', 'Confused'),
        ('stressed', 'Stressed'),
        ('disengaged', 'Disengaged'),
        ('neutral', 'Neutral'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_sessions')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='sessions')
    
    # Session tracking
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Adaptive parameters
    current_question_index = models.IntegerField(default=0)
    current_difficulty_level = models.IntegerField(default=3)  # Start at medium
    student_ability = models.FloatField(default=0.0, help_text="IRT ability estimate (theta)")
    
    # Scoring
    total_score = models.FloatField(default=0.0)
    behavior_score = models.FloatField(default=0.0)
    correct_answers = models.IntegerField(default=0)
    incorrect_answers = models.IntegerField(default=0)
    
    # Behavior tracking
    total_tab_switches = models.IntegerField(default=0)
    total_fullscreen_violations = models.IntegerField(default=0, help_text="Total times user exited fullscreen")
    total_no_face_violations = models.IntegerField(default=0, help_text="Total times no face was detected")
    total_hesitations = models.IntegerField(default=0)
    avg_response_time = models.FloatField(default=0.0, help_text="Average response time in seconds")
    
    # Time tracking for pause/resume
    accumulated_time = models.FloatField(default=0.0, help_text="Total active time in seconds")
    last_activity_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp of last user interaction")
    
    attempt_number = models.IntegerField(default=1, help_text="Attempt number for this quiz")
    
    # Classroom context (null if general quiz)
    classroom_assignment = models.ForeignKey(
        'users.ClassroomQuizAssignment', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='sessions',
        help_text="Link to classroom assignment if this is a classroom quiz"
    )
    classroom_attempt_number = models.IntegerField(default=1, help_text="Attempt number for this classroom assignment")
    
    # Mindset detection
    detected_mindset = models.CharField(max_length=20, choices=MINDSET_CHOICES, default='neutral')
    
    class Meta:
        db_table = 'quiz_sessions'
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.quiz.title} ({self.started_at.strftime('%Y-%m-%d %H:%M')})"
    
    @property
    def accuracy(self):
        total = self.correct_answers + self.incorrect_answers
        if total == 0:
            return 0
        return (self.correct_answers / total) * 100


class Response(models.Model):
    """Individual question response within a quiz session"""
    session = models.ForeignKey(QuizSession, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='responses')
    
    # Answer data
    # For MCQ
    selected_answer = models.CharField(max_length=1, choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')], blank=True)
    is_correct = models.BooleanField(default=False)
    
    # Behavior metrics
    response_time = models.FloatField(help_text="Time taken to answer in seconds")
    hesitation_count = models.IntegerField(default=0, help_text="Number of times answer was changed")
    tab_switches = models.IntegerField(default=0, help_text="Number of tab switches during this question")
    
    # Confidence and difficulty
    confidence_level = models.FloatField(default=0.5, help_text="Calculated confidence (0-1)")
    question_difficulty_at_time = models.IntegerField(help_text="Difficulty level when question was presented")
    
    # Timestamps
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'responses'
        ordering = ['timestamp']
    
    def __str__(self):
        return f"Q{self.question.id} - {'✓' if self.is_correct else '✗'}"
    
    def save(self, *args, **kwargs):
        # Auto-determine if answer is correct (Only for MCQ)
        if hasattr(self.question, 'question_type') and self.question.question_type == 'mcq':
            self.is_correct = (self.selected_answer == self.question.correct_answer)
        
        # Calculate confidence based on response time and hesitation
        if self.response_time < 5 and self.hesitation_count == 0:
            self.confidence_level = 0.9
        elif self.response_time < 10 and self.hesitation_count <= 1:
            self.confidence_level = 0.7
        elif self.response_time < 20 and self.hesitation_count <= 2:
            self.confidence_level = 0.5
        else:
            self.confidence_level = 0.3
        
        super().save(*args, **kwargs)




class QuizAssignment(models.Model):
    """Link between a Quiz and a Classroom"""
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='assignments')
    classroom = models.ForeignKey('users.Classroom', on_delete=models.CASCADE, related_name='quiz_assignments')
    
    # Assignment metadata
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='quiz_assignments_created')
    assigned_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(null=True, blank=True)
    
    # Gating: Prerequisite Learning Module
    prerequisite_module = models.ForeignKey(
        'learning.LearningModule', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='quiz_assignments',
        help_text="Student must complete this module before taking the quiz"
    )
    
    # Quiz mode and settings
    class Meta:
        db_table = 'quiz_assignments'
        unique_together = ['quiz', 'classroom']
        ordering = ['-assigned_at']
        
    def __str__(self):
        return f"{self.quiz.title} assigned to {self.classroom.name}"



class QuizResetLog(models.Model):
    """Audit log for quiz attempt resets"""
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    teacher = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='reset_actions')
    target_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reset_received')
    quiz = models.ForeignKey(Quiz, on_delete=models.SET_NULL, null=True, blank=True)
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
    
    def __str__(self):
        return f"{self.teacher.email if self.teacher else 'Unknown'} reset {self.sessions_deleted} sessions"


class AIGeneratedQuestion(models.Model):
    """Track AI-generated questions for audit and quality control"""
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='ai_generation_metadata')
    generation_prompt = models.TextField(help_text="The prompt sent to the AI model")
    model_used = models.CharField(max_length=50, help_text="AI model name (e.g., gpt-4o, gemini-pro)")
    generation_metadata = models.JSONField(default=dict, help_text="Tokens used, cost, generation time, etc.")
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='ai_generated_questions')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_ai_questions')
    is_approved = models.BooleanField(default=False, help_text="Whether the teacher approved this question")
    
    # AI Quality Metrics
    confidence_score = models.FloatField(null=True, blank=True, help_text="AI's self-reported confidence (0.0-1.0)")
    suggested_difficulty = models.IntegerField(null=True, blank=True, help_text="AI's suggested difficulty level (1-5)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'ai_generated_questions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"AI Question ({self.model_used}) - {self.question.question_text[:50]}..."

