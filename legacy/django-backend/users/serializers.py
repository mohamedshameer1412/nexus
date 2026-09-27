from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()

# Import models for serializers
from .models import (
    Classroom, ClassroomInvitation, Notification, 
    ClassroomLeaveRequest, LearningProfile, MasteryVector, ClassroomQuizAssignment,
    Achievement
)


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password2', 'role', 'first_name', 
                  'last_name', 'phone_number', 'date_of_birth', 'grade_level')
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
            'date_of_birth': {'required': True},
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        
                
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""
    full_name = serializers.ReadOnlyField()
    profile_picture = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'role', 'first_name', 'last_name', 
                  'full_name', 'phone_number', 'date_of_birth', 'profile_picture',
                  'grade_level', 'preference_dark_mode', 
                  'preference_email_notifications', 'created_at', 'last_active')
        read_only_fields = ('id', 'username', 'created_at', 'last_active')

    def get_profile_picture(self, obj):
        """Return full URL for profile picture"""
        if obj.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_picture.url)
            return obj.profile_picture.url
        return None



class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile"""
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'phone_number', 'date_of_birth', 
                  'profile_picture', 'grade_level',
                  'preference_dark_mode', 'preference_email_notifications')


from .models import Classroom

class ClassroomSerializer(serializers.ModelSerializer):
    teacher_name = serializers.ReadOnlyField(source='teacher.full_name')
    teacher_email = serializers.ReadOnlyField(source='teacher.email')
    teacher_phone = serializers.ReadOnlyField(source='teacher.phone_number')
    student_count = serializers.SerializerMethodField()
    quizzes_count = serializers.SerializerMethodField()
    is_enrolled = serializers.SerializerMethodField()
    is_co_teacher = serializers.SerializerMethodField()
    co_teacher_names = serializers.SerializerMethodField()

    class Meta:
        model = Classroom
        fields = ('id', 'name', 'teacher', 'teacher_name', 'teacher_email', 'teacher_phone',
                 'co_teachers', 'co_teacher_names',
                 'created_at', 'student_count', 'quizzes_count', 'is_enrolled', 'is_co_teacher', 
                 'access_code', 'is_join_by_code_enabled')
        read_only_fields = ('id', 'teacher', 'created_at', 'access_code')

    def get_student_count(self, obj):
        return obj.students.count()

    def get_quizzes_count(self, obj):
        try:
            return obj.assigned_quizzes.count()
        except AttributeError:
             # Fallback if migration hasn't run or using old name
            return getattr(obj, 'quiz_assignments', obj.assigned_quizzes).count()

    def get_is_enrolled(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.students.filter(id=request.user.id).exists()
        return False
    
    def get_is_co_teacher(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.co_teachers.filter(id=request.user.id).exists()
        return False
    
    def get_co_teacher_names(self, obj):
        return [teacher.full_name for teacher in obj.co_teachers.all()]

class UserDetailSerializer(serializers.ModelSerializer):
    """Simple serializer for nested user lists"""
    class Meta:
        model = User
        fields = ('id', 'full_name', 'username', 'email', 'phone_number', 'profile_picture', 'date_joined')


class ClassroomDetailSerializer(ClassroomSerializer):
    students = serializers.SerializerMethodField()
    
    class Meta(ClassroomSerializer.Meta):
        fields = ClassroomSerializer.Meta.fields + ('students',)

    def get_students(self, obj):
        request = self.context.get('request')
        if not request:
            return []
            
        user = request.user
        is_teacher = user.role == 'teacher' or user.id == obj.teacher_id or obj.co_teachers.filter(id=user.id).exists()
        
        if is_teacher:
            # Teachers get full contact details
            return UserDetailSerializer(obj.students.all(), many=True).data
        elif user.role == 'student':
            # Students see classmates but NO contact info
            students = obj.students.all()
            data = UserDetailSerializer(students, many=True).data
            for s in data:
                if s['id'] != str(user.id): # Keep own info, scrub others
                    s['email'] = None
                    s['phone_number'] = None
            return data
        return []

from .models import ClassroomInvitation

class ClassroomInvitationSerializer(serializers.ModelSerializer):
    classroom_name = serializers.ReadOnlyField(source='classroom.name')
    teacher_name = serializers.ReadOnlyField(source='classroom.teacher.full_name')

    class Meta:
        model = ClassroomInvitation
        fields = ('id', 'classroom', 'classroom_name', 'teacher_name', 'email', 'status', 'created_at')
        read_only_fields = ('id', 'classroom', 'email', 'status', 'created_at')


from .models import Notification, ClassroomLeaveRequest


class ClassroomLeaveRequestSerializer(serializers.ModelSerializer):
    student_name = serializers.ReadOnlyField(source='student.full_name')
    student_email = serializers.ReadOnlyField(source='student.email')
    
    class Meta:
        model = ClassroomLeaveRequest
        fields = ('id', 'classroom', 'student', 'student_name', 'student_email', 'status', 'reason', 'created_at', 'responded_at')
        read_only_fields = ('id', 'student', 'status', 'created_at', 'responded_at')


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications"""
    
    class Meta:
        model = Notification
        fields = ('id', 'user', 'title', 'message', 'notification_type', 'is_read', 
                 'related_object_id', 'related_object_type', 'created_at')
        read_only_fields = ('id', 'user', 'created_at')




# ==================== LEARNING DNA SERIALIZERS ====================

from .models import LearningProfile, SubjectConfidence, MasteryVector


class SubjectConfidenceSerializer(serializers.ModelSerializer):
    """Serializer for subject confidence"""
    subject_display = serializers.CharField(source='get_subject_display', read_only=True)
    
    class Meta:
        model = SubjectConfidence
        fields = ('id', 'subject', 'subject_display', 'confidence_level', 
                 'actual_performance', 'confidence_accuracy', 'created_at', 'updated_at')
        read_only_fields = ('id', 'actual_performance', 'confidence_accuracy', 'created_at', 'updated_at')
    
    def validate_confidence_level(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Confidence level must be between 1 and 5")
        return value


class LearningProfileSerializer(serializers.ModelSerializer):
    """Serializer for learning profile"""
    subject_confidences = SubjectConfidenceSerializer(many=True, read_only=True)
    learning_style_display = serializers.CharField(source='get_learning_style_display', read_only=True)
    diagnostic_history = serializers.SerializerMethodField()
    
    class Meta:
        model = LearningProfile
        fields = ('id', 'user', 'learning_style', 'learning_style_display', 
                 'preferred_study_time', 'initial_ability', 'current_ability',
                 'learning_speed', 'guessing_tendency', 'consistency_score',
                 'avg_session_duration', 'total_study_time', 
                 'onboarding_completed_at', 'created_at', 'updated_at',
                 'subject_confidences', 'diagnostic_history')
        read_only_fields = ('id', 'user', 'initial_ability', 'current_ability',
                           'learning_speed', 'guessing_tendency', 'consistency_score',
                           'avg_session_duration', 'total_study_time',
                           'onboarding_completed_at', 'created_at', 'updated_at')

    def get_diagnostic_history(self, obj):
        """Return history of diagnostic test attempts"""
        from quiz.models import QuizSession
        sessions = QuizSession.objects.filter(
            user=obj.user,
            quiz__title__iexact="Diagnostic Test",
            completed_at__isnull=False
        ).order_by('completed_at')
        
        return [
            {
                'session_id': str(s.id),
                'completed_at': s.completed_at,
                'ability_score': round(s.student_ability, 3),
                'accuracy': round((s.correct_answers / (s.correct_answers + s.incorrect_answers) * 100) if (s.correct_answers + s.incorrect_answers) > 0 else 0, 2),
                'correct_answers': s.correct_answers,
                'incorrect_answers': s.incorrect_answers,
                'total_score': round(s.total_score, 2),
                'attempt_number': s.attempt_number
            } for s in sessions
        ]


class LearningProfileCreateSerializer(serializers.Serializer):
    """Serializer for creating learning profile during onboarding"""
    learning_style = serializers.ChoiceField(
        choices=['visual', 'reading', 'problem_solving', 'explanation'],
        required=True
    )
    preferred_study_time = serializers.ChoiceField(
        choices=['morning', 'afternoon', 'evening', 'night'],
        required=False,
        allow_null=True
    )
    subject_confidences = serializers.ListField(
        child=serializers.DictField(),
        required=True,
        min_length=1
    )
    
    def validate_subject_confidences(self, value):
        """Validate subject confidence data"""
        valid_subjects = ['mathematics', 'science', 'english', 'social_studies', 'hindi', 'computer_science']
        
        for item in value:
            if 'subject' not in item or 'confidence_level' not in item:
                raise serializers.ValidationError("Each subject confidence must have 'subject' and 'confidence_level'")
            
            if item['subject'] not in valid_subjects:
                raise serializers.ValidationError(f"Invalid subject: {item['subject']}")
            
            if not isinstance(item['confidence_level'], int) or item['confidence_level'] < 1 or item['confidence_level'] > 5:
                raise serializers.ValidationError("Confidence level must be an integer between 1 and 5")
        
        return value


class MasteryVectorSerializer(serializers.ModelSerializer):
    """Serializer for mastery vector"""
    accuracy = serializers.SerializerMethodField()
    
    class Meta:
        model = MasteryVector
        fields = ('id', 'user', 'concept_id', 'mastery_score', 'attempts_count',
                 'correct_count', 'accuracy', 'total_time_spent', 'last_practiced_at',
                 'initial_score', 'peak_score', 'recent_trend', 'created_at', 'updated_at')
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')
    
    def get_accuracy(self, obj):
        if obj.attempts_count == 0:
            return 0.0
        return round((obj.correct_count / obj.attempts_count) * 100, 2)


class MasteryDashboardSerializer(serializers.Serializer):
    """Serializer for mastery dashboard response"""
    overall_mastery = serializers.FloatField()
    total_concepts = serializers.IntegerField()
    mastered_concepts = serializers.IntegerField()
    weak_concepts = MasteryVectorSerializer(many=True)
    strong_concepts = MasteryVectorSerializer(many=True)
    mastery_by_subject = serializers.DictField()


# ==================== CLASSROOM QUIZ ASSIGNMENT SERIALIZERS ====================

class ClassroomQuizAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for classroom quiz assignments"""
    classroom_name = serializers.CharField(source='classroom.name', read_only=True)
    quiz_title = serializers.CharField(source='quiz.title', read_only=True)
    quiz_description = serializers.CharField(source='quiz.description', read_only=True)
    quiz_time_limit = serializers.IntegerField(source='quiz.time_limit', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.full_name', read_only=True)
    question_count = serializers.SerializerMethodField()
    
    # UI Compatibility Aliases
    title = serializers.CharField(source='quiz.title', read_only=True)
    time_limit_minutes = serializers.IntegerField(source='quiz.time_limit', read_only=True)
    total_marks = serializers.IntegerField(source='quiz.total_questions', read_only=True)
    assignment_id = serializers.CharField(source='id', read_only=True)

    # Student-specific fields
    attempts_used = serializers.SerializerMethodField()
    attempts_remaining = serializers.SerializerMethodField()
    last_attempt_score = serializers.SerializerMethodField()
    
    class Meta:
        model = ClassroomQuizAssignment
        fields = (
            'id', 'assignment_id', 'classroom', 'classroom_name', 'quiz', 'quiz_title', 'quiz_description', 'quiz_time_limit',
            'title', 'time_limit_minutes', 'total_marks',
            'assigned_by', 'assigned_by_name', 'assigned_at', 'due_date',
            'quiz_mode', 'allow_unlimited_attempts', 'show_immediate_feedback',
            'max_attempts', 'strict_time_limit', 'enable_proctoring', 'shuffle_questions',
            'show_results_after_due', 'is_active',
            'attempts_used', 'attempts_remaining', 'last_attempt_score',
            'question_count'
        )
        read_only_fields = ('id', 'assigned_by', 'assigned_at')
    
    def get_question_count(self, obj):
        """Get number of questions in the quiz"""
        return obj.quiz.total_questions

    def get_attempts_used(self, obj):
        """Get number of attempts used by current user"""
        request = self.context.get('request')
        if not (request and hasattr(request, 'user')):
            return 0
            
        user = request.user
        target_user = user

        from quiz.models import QuizSession
        return QuizSession.objects.filter(
            classroom_assignment=obj,
            user=target_user
        ).count()
    
    def get_attempts_remaining(self, obj):
        """Get remaining attempts for current user"""
        if obj.quiz_mode == 'practice' and obj.allow_unlimited_attempts:
            return -1  # Unlimited
        attempts_used = self.get_attempts_used(obj)
        return max(0, obj.max_attempts - attempts_used)
    
    def get_last_attempt_score(self, obj):
        """Get score from last attempt of current user"""
        request = self.context.get('request')
        if not (request and hasattr(request, 'user')):
             return None
             
        user = request.user
        target_user = user

        from quiz.models import QuizSession
        last_session = QuizSession.objects.filter(
            classroom_assignment=obj,
            user=target_user,
            completed_at__isnull=False
        ).order_by('-completed_at').first()
        
        if last_session:
            return round(last_session.total_score, 2)
        return None


class AchievementSerializer(serializers.ModelSerializer):
    """Serializer for user achievements/badges"""
    class Meta:
        model = Achievement
        fields = ('id', 'achievement_type', 'title', 'description', 'icon_type', 'earned_at')
        read_only_fields = ('id', 'earned_at')
