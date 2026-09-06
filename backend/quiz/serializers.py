from rest_framework import serializers
from .models import Topic, Subtopic, Question, Quiz, QuizSession, Response



class TopicSerializer(serializers.ModelSerializer):
    """Serializer for Topic model"""
    subtopics_count = serializers.SerializerMethodField()
    questions_count = serializers.SerializerMethodField()
    approved_questions_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Topic
        fields = ('id', 'name', 'description', 'subtopics_count', 'questions_count', 'approved_questions_count', 'created_at')
    
    def get_subtopics_count(self, obj):
        return obj.subtopics.count()

    def get_questions_count(self, obj):
        return obj.questions.count()

    def get_approved_questions_count(self, obj):
        return obj.questions.filter(is_approved=True).count()


class SubtopicSerializer(serializers.ModelSerializer):
    """Serializer for Subtopic model"""
    topic_name = serializers.CharField(source='topic.name', read_only=True)
    prerequisite_names = serializers.SerializerMethodField()
    
    class Meta:
        model = Subtopic
        fields = ('id', 'topic', 'topic_name', 'name', 'description', 
                  'prerequisite_subtopics', 'prerequisite_names', 'created_at')
    
    def get_prerequisite_names(self, obj):
        return [prereq.name for prereq in obj.prerequisite_subtopics.all()]


class QuestionSerializer(serializers.ModelSerializer):
    """Serializer for Question model"""
    topic_name = serializers.CharField(source='topic.name', read_only=True)
    subtopic_name = serializers.CharField(source='subtopic.name', read_only=True)
    success_rate = serializers.ReadOnlyField()
    
    class Meta:
        model = Question
        fields = ('id', 'topic', 'topic_name', 'subtopic', 'subtopic_name',
                  'question_type',
                  'question_text', 'image', 'option_a', 'option_b', 'option_c', 'option_d',
                  'correct_answer', 
                  'difficulty_level', 'irt_difficulty', 
                  'irt_discrimination', 'explanation', 'success_rate', 'is_approved',
                  'times_asked', 'times_correct', 'created_at')
        read_only_fields = ('times_asked', 'times_correct', 'created_at')
    
    def validate(self, data):
        """Validate question data"""
        question_type = data.get('question_type', 'mcq')

        if question_type == 'mcq':
            # Check for duplicate options
            options = [
                data.get('option_a', ''),
                data.get('option_b', ''),
                data.get('option_c', ''),
                data.get('option_d', '')
            ]
            # Filter out empty strings if relevant, but strict check is usually good
            options = [opt for opt in options if opt] # Ignore empty input
            if len(options) > 0 and len(options) != len(set(options)):
                raise serializers.ValidationError("All options must be unique")
        
        # Validate question text length
        
        # Validate question text length
        question_text = data.get('question_text', '')
        if len(question_text) < 10:
            raise serializers.ValidationError("Question must be at least 10 characters long")
        if len(question_text) > 1000:
            raise serializers.ValidationError("Question must not exceed 1000 characters")
        
        return data


class QuestionListSerializer(serializers.ModelSerializer):
    """Serializer for listing questions with all fields needed for editing"""
    topic_name = serializers.CharField(source='topic.name', read_only=True)
    subtopic_name = serializers.CharField(source='subtopic.name', read_only=True)
    
    class Meta:
        model = Question
        fields = ('id', 'topic', 'topic_name', 'subtopic', 'subtopic_name', 
                  'question_type', 'question_text', 'image',
                  'option_a', 'option_b', 'option_c', 'option_d',
                  'correct_answer', 'explanation', 
                  'difficulty_level', 'success_rate')



class QuestionDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for a single question (for quiz taking)"""
    class Meta:
        model = Question
        fields = ('id', 'question_text', 'question_type', 'image', 'option_a', 'option_b', 
                  'option_c', 'option_d', 'difficulty_level')


class QuizSerializer(serializers.ModelSerializer):
    """Serializer for Quiz model"""
    topics_names = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    attempts_count = serializers.SerializerMethodField()
    active_session_id = serializers.SerializerMethodField()
    question_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Quiz
        fields = ('id', 'title', 'description', 'topics', 'topics_names',
                  'total_questions', 'time_limit', 'is_adaptive', 'is_active',
                  'question_type',
                  'allow_retakes', 'max_attempts', 'show_answers', 'show_explanations',
                  'created_by', 'created_by_name', 'created_at', 'attempts_count', 
                  'active_session_id', 'question_count')
        read_only_fields = ('created_by', 'created_at')
    
    def get_topics_names(self, obj):
        return [topic.name for topic in obj.topics.all()]

    def get_attempts_count(self, obj):
        """Get number of attempts for the current user"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return QuizSession.objects.filter(quiz=obj, user=request.user).count()
        return 0

    def get_active_session_id(self, obj):
        """Get ID of any active session for this quiz"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            from .models import QuizSession
            active_session = QuizSession.objects.filter(
                quiz=obj, 
                user=request.user, 
                is_active=True
            ).first()
            return str(active_session.id) if active_session else None
        return None
    
    def get_question_count(self, obj):
        """Get the actual number of questions available for this quiz based on its topics"""
        quiz_topics = obj.topics.all()
        return Question.objects.filter(topic__in=quiz_topics).count()
    
    def validate(self, data):
        """Validate quiz configuration"""
        # Validate title length
        title = data.get('title', '')
        if len(title) < 3:
            raise serializers.ValidationError({"title": "Title must be at least 3 characters long"})
        
        # Validate total_questions
        total_questions = data.get('total_questions', 0)
        if total_questions < 1:
            raise serializers.ValidationError({"total_questions": "Must have at least 1 question"})
        if total_questions > 100:
            raise serializers.ValidationError({"total_questions": "Cannot exceed 100 questions"})
        
        # Validate time_limit if set
        time_limit = data.get('time_limit')
        if time_limit is not None:
            if time_limit < 1:
                raise serializers.ValidationError({"time_limit": "Time limit must be at least 1 minute"})
            if time_limit > 1440:
                raise serializers.ValidationError({"time_limit": "Time limit cannot exceed 24 hours (1440 minutes)"})
        
        # Validate max_attempts
        allow_retakes = data.get('allow_retakes', False)
        max_attempts = data.get('max_attempts', 1)
        if allow_retakes and max_attempts < 1:
            print(f"Validation Error: max_attempts {max_attempts} with allow_retakes")
            raise serializers.ValidationError({"max_attempts": "Must allow at least 1 attempt when retakes are enabled"})
        if max_attempts > 100:
            print(f"Validation Error: max_attempts {max_attempts} > 100")
            raise serializers.ValidationError({"max_attempts": "Cannot exceed 100 attempts"})
        
        # Validate that total_questions doesn't exceed available questions in selected topics
        topics = data.get('topics', [])
        if topics and total_questions:
            from .models import Question
            # Filter only approved questions and match question type (if applicable)
            # Since we only support MCQ now, we prioritize MCQ count, but old data might exist.
            # Assuming all active questions should be countable.
            available_questions = Question.objects.filter(topic__in=topics, is_approved=True).count()
            
            print(f"DEBUG: validate_quiz: topics={topics}, total_questions={total_questions}, available={available_questions}")
            
            if total_questions > available_questions:
                # If we have 0 questions, provide a helpful message
                if available_questions == 0:
                     print("Validation Error: No questions available in selected topics")
                     raise serializers.ValidationError({
                        "total_questions": "The selected topics do not have any approved questions. Please add questions to these topics first."
                    })
                
                print(f"Validation Error: total_questions {total_questions} > {available_questions}")
                raise serializers.ValidationError({
                    "total_questions": f"Cannot create quiz with {total_questions} questions. Only {available_questions} approved questions available in selected topics."
                })
        
        return data


class QuizSessionSerializer(serializers.ModelSerializer):
    """Serializer for QuizSession model"""
    quiz_title = serializers.CharField(source='quiz.title', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    accuracy = serializers.ReadOnlyField()
    question_count = serializers.IntegerField(source='quiz.total_questions', read_only=True)
    time_spent = serializers.SerializerMethodField()
    
    class Meta:
        model = QuizSession
        fields = ('id', 'user', 'user_name', 'quiz', 'quiz_title', 'question_count',
                  'started_at', 'completed_at', 'is_active',
                  'current_question_index', 'current_difficulty_level',
                  'student_ability', 'total_score', 'behavior_score',
                  'correct_answers', 'incorrect_answers', 'accuracy',
                  'total_tab_switches', 'total_hesitations',
                  'avg_response_time', 'time_spent', 'detected_mindset',
                  'attempt_number')
        read_only_fields = ('user', 'started_at', 'completed_at')

    def get_time_spent(self, obj):
        # Convert seconds to minutes
        return obj.accumulated_time / 60.0 if obj.accumulated_time else 0.0


class QuizSessionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new quiz session"""
    class Meta:
        model = QuizSession
        fields = ('quiz',)


class ResponseSerializer(serializers.ModelSerializer):
    """Serializer for Response model"""
    question_text = serializers.CharField(source='question.question_text', read_only=True)
    correct_answer = serializers.CharField(source='question.correct_answer', read_only=True)
    explanation = serializers.CharField(source='question.explanation', read_only=True)
    your_answer = serializers.SerializerMethodField()
    
    class Meta:
        model = Response
        fields = ('id', 'session', 'question', 'question_text',
                  'selected_answer', 'your_answer', 'is_correct', 'response_time',
                  'correct_answer', 'explanation',
                  'hesitation_count', 'tab_switches', 'confidence_level',
                  'question_difficulty_at_time', 'timestamp')
        read_only_fields = ('is_correct', 'confidence_level', 'timestamp', 
                            'correct_answer', 'explanation')

    def get_your_answer(self, obj):
        return obj.selected_answer


class ResponseSubmitSerializer(serializers.Serializer):
    """Serializer for submitting an answer"""
    question_id = serializers.UUIDField()  # Changed from IntegerField to match Question model
    # selected_answer is optional for text questions
    selected_answer = serializers.ChoiceField(choices=['A', 'B', 'C', 'D'], required=False, allow_null=True)
    
    response_time = serializers.FloatField()
    hesitation_count = serializers.IntegerField(default=0)
    tab_switches = serializers.IntegerField(default=0)
