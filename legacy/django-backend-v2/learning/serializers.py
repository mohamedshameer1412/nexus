from rest_framework import serializers
from .models import LearningModule, FlashcardDeck, Flashcard, StudentModuleProgress
from quiz.models import Question
from quiz.serializers import QuestionSerializer

class FlashcardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flashcard
        fields = ['id', 'front', 'back', 'is_ai_generated', 'is_approved']

class FlashcardDeckSerializer(serializers.ModelSerializer):
    cards = serializers.SerializerMethodField()
    card_count = serializers.SerializerMethodField()
    
    class Meta:
        model = FlashcardDeck
        fields = ['id', 'name', 'is_published', 'created_at', 'cards', 'card_count']

    def get_cards(self, obj):
        # Only show approved cards to everyone
        # But teachers can see all cards in this view too
        request = self.context.get('request')
        if request and request.user.is_authenticated and request.user.role == 'teacher':
            queryset = obj.cards.all()
        else:
            queryset = obj.cards.filter(is_approved=True)
        return FlashcardSerializer(queryset, many=True).data

    def get_card_count(self, obj):
        request = self.context.get('request')
        total = obj.cards.count()
        approved = obj.cards.filter(is_approved=True).count()
        
        if request and request.user.is_authenticated and request.user.role == 'teacher':
            return {
                'approved': approved,
                'total': total
            }
        return approved

class LearningModuleListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing modules.
    Excludes heavy nested relationships like questions and flashcards.
    """
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    topic_name = serializers.CharField(source='topic.name', read_only=True)
    flashcard_count = serializers.SerializerMethodField()
    quiz_count = serializers.IntegerField(source='quiz_set.count', read_only=True, required=False) # Assuming quiz_set or similar
    type = serializers.SerializerMethodField()
    processing_status = serializers.SerializerMethodField()

    class Meta:
        model = LearningModule
        fields = [
            'id', 'title', 'description', 
            'classroom', 'topic', 'topic_name',
            'is_published', 'created_by_name', 
            'created_at', 'updated_at',
            'flashcard_count', 'quiz_count',
            'type', 'processing_status'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def get_flashcard_count(self, obj):
        request = self.context.get('request')
        total = 0
        approved = 0
        for deck in obj.flashcard_decks.all():
            total += deck.cards.count()
            approved += deck.cards.filter(is_approved=True).count()
            
        if request and request.user.is_authenticated and request.user.role == 'teacher':
            return {
                'approved': approved,
                'total': total
            }
        return approved

    def get_type(self, obj):
        if obj.pdf_file:
            return 'pdf'
        return 'text'

    def get_processing_status(self, obj):
        if obj.pdf_file and not obj.content_text:
            return 'processing'
        return 'completed'

class LearningModuleDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for single module view.
    Includes all nested content.
    """
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    flashcard_decks = FlashcardDeckSerializer(many=True, read_only=True)
    quizzes = serializers.SerializerMethodField()
    questions = serializers.SerializerMethodField()
    
    class Meta:
        model = LearningModule
        fields = [
            'id', 'title', 'description', 
            'pdf_file', 'content_text', 
            'classroom', 'topic', 
            'is_published', 'created_by_name', 
            'created_at', 'updated_at',
            'flashcard_decks', 'quizzes', 'questions'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'content_text']

    def get_quizzes(self, obj):
        # Return quizzes that require this module as a prerequisite
        if hasattr(obj, 'dependent_quizzes'):
            assignments = obj.dependent_quizzes.filter(is_active=True)
            return [{
                'id': a.quiz.id,
                'title': a.quiz.title,
                'due_date': a.due_date
            } for a in assignments]
        return []

    def get_questions(self, obj):
        request = self.context.get('request')
        # Fetch questions linked directly to this module
        from quiz.models import Question
        from quiz.serializers import QuestionSerializer
        
        queryset = Question.objects.filter(learning_module=obj)
        
        # NOTE: For teachers, we return everything so they can see drafts in the preview tab
        if not (request and request.user.is_authenticated and request.user.role == 'teacher'):
            queryset = queryset.filter(is_approved=True)
            
        return QuestionSerializer(queryset, many=True).data

class StudentModuleProgressSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.username', read_only=True)
    module_title = serializers.CharField(source='module.title', read_only=True)
    
    class Meta:
        model = StudentModuleProgress
        fields = [
            'id', 'student', 'student_name', 
            'module', 'module_title',
            'status', 'time_spent_seconds', 
            'last_accessed_at', 'completion_percentage',
            'flashcards_studied_count'
        ]
        read_only_fields = ['student', 'module', 'last_accessed_at']
