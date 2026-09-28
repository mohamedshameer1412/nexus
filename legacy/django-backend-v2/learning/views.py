from rest_framework import viewsets, permissions, status, filters, exceptions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import LearningModule, FlashcardDeck, Flashcard, StudentModuleProgress
from .serializers import LearningModuleListSerializer, LearningModuleDetailSerializer, FlashcardDeckSerializer, StudentModuleProgressSerializer, FlashcardSerializer
from .utils import extract_text_from_pdf
from users.models import Classroom, User as UserAuth
from quiz.models import Question, AIGeneratedQuestion, Quiz, Topic

class IsTeacherOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.role == 'teacher'

class LearningModuleViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'description']

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data
        # Add approved questions for Knowledge Prep
        questions = Question.objects.filter(learning_module=instance, is_approved=True)
        data['questions'] = [
            {
                'id': q.id,
                'question_text': q.question_text,
                'question_type': q.question_type,
                'option_a': getattr(q, 'option_a', None),
                'option_b': getattr(q, 'option_b', None),
                'option_c': getattr(q, 'option_c', None),
                'option_d': getattr(q, 'option_d', None),
                'correct_answer': getattr(q, 'correct_answer', None),
                'explanation': getattr(q, 'explanation', None),
                'model_answer': getattr(q, 'model_answer', None),
                'required_keywords': getattr(q, 'required_keywords', None),
            } for q in questions
        ]
        return Response(data)
    
    def get_serializer_class(self):
        if self.action == 'list':
            return self.get_serializer_module().LearningModuleListSerializer
        return self.get_serializer_module().LearningModuleDetailSerializer

    def get_serializer_module(self):
        # Lazy import to avoid circular dependency if any, though likely not needed here but good practice
        from . import serializers
        return serializers
    
    def get_queryset(self):
        user = self.request.user
        queryset = LearningModule.objects.all()
        
        # Optimization: Prefetch related data to avoid N+1
        if self.action != 'list':
            queryset = queryset.select_related('classroom', 'topic', 'created_by') \
                               .prefetch_related('flashcard_decks__cards', 'dependent_quizzes__quiz')

        if user.role == 'student':
            # Students see modules from their enrolled classes where they participate
            return queryset.filter(
                classroom__students=user,
                is_published=True
            )
        elif user.role == 'teacher':
            # Teachers see modules from their created classes
            return queryset.filter(classroom__teacher=user)
        return LearningModule.objects.none()

    def perform_create(self, serializer):
        if self.request.user.role != 'teacher':
            raise exceptions.PermissionDenied("Only teachers can create modules")
        
        pdf_file = self.request.FILES.get('pdf_file')
        content_text = ""
        if pdf_file:
            # Save temporary file for extraction
            from django.core.files.storage import default_storage
            from django.core.files.base import ContentFile
            path = default_storage.save('tmp/pdf_extract.pdf', ContentFile(pdf_file.read()))
            full_path = default_storage.path(path)
            content_text = extract_text_from_pdf(full_path)
            default_storage.delete(path)
        
        serializer.save(
            created_by=self.request.user,
            content_text=content_text
        )

    @action(detail=True, methods=['post'])
    def generate_ai_content(self, request, pk=None):
        """
        Trigger AI generation for this module (Flashcards, Quiz, Long Answer).
        Options: types=['quiz', 'essay', 'flashcard'], mode='ai'
        """
        module = self.get_object()
        text_content = module.content_text
        requested_types = request.data.get('types', [])
        mode = request.data.get('mode', 'ai')

        if not text_content:
            return Response({"error": "No content text found in module. Please upload a PDF with extractable text."}, status=status.HTTP_400_BAD_REQUEST)

        from utils.gemini_service import get_gemini_service
        gemini = get_gemini_service()

        results = {}

        print(f"Generating AI content for module {module.id}. Requested types: {requested_types}")
        print(f"Content length: {len(text_content)} characters")

        # 1. Generate Flashcards
        if 'flashcard' in requested_types:
            try:
                flashcards_data = gemini.generate_flashcards(text_content, count=10)
                print(f"Flashcards data received: {len(flashcards_data) if flashcards_data else 0} items")
                if flashcards_data:
                    deck, _ = FlashcardDeck.objects.get_or_create(
                        module=module,
                        name=f"{module.title} - Flashcards",
                        defaults={'is_published': False}
                    )
                    created_count = 0
                    for card in flashcards_data:
                        Flashcard.objects.create(
                            deck=deck,
                            front=card.get('front', ''),
                            back=card.get('back', ''),
                            is_ai_generated=True,
                            is_approved=False
                        )
                        created_count += 1
                    results["flashcards_created"] = created_count
            except Exception as e:
                print(f"Flashcard generation failed: {e}")
                results["flashcards_error"] = str(e)

        # 1.5 Ensure a valid Topic exists for Questions
        from quiz.models import Topic
        topic = module.topic
        if not topic:
            # Try to find or create a default topic
            topic, created = Topic.objects.get_or_create(
                name="General Knowledge",
                defaults={"description": "Auto-generated topic for AI modules"}
            )
            # Link module to this topic if it doesn't have one
            module.topic = topic
            module.save()
            print(f"Associated module with topic: {topic.name}")

        # 2. Generate MCQs (Quiz)
        if 'quiz' in requested_types:
            try:
                questions_data = gemini.generate_questions_from_text(text_content, count=5, question_type='mcq')
                print(f"MCQ data received: {len(questions_data) if questions_data else 0} items")
                if questions_data:
                    created_count = 0
                    for q_data in questions_data:
                        try:
                            # More flexible field getting
                            q_text = q_data.get('question_text') or q_data.get('question')
                            if not q_text:
                                continue

                            options = q_data.get('options', {})
                            question = Question.objects.create(
                                topic=topic,
                                question_text=q_text,
                                question_type='mcq',
                                option_a=options.get('A', 'Option A'),
                                option_b=options.get('B', 'Option B'),
                                option_c=options.get('C', 'Option C'),
                                option_d=options.get('D', 'Option D'),
                                correct_answer=q_data.get('correct_answer', 'A'),
                                explanation=q_data.get('explanation', ''),
                                learning_module=module,
                                created_by=request.user,
                                is_approved=False
                            )
                            AIGeneratedQuestion.objects.create(
                                question=question,
                                generation_prompt=f"Generated from module {module.id}",
                                model_used="Gemini-Flash",
                                generated_by=request.user,
                                is_approved=False,
                                confidence_score=q_data.get('confidence_score', 0.8),
                                suggested_difficulty=q_data.get('difficulty', 3)
                            )
                            created_count += 1
                        except Exception as inner_e:
                            print(f"Failed to create individual MCQ: {inner_e}")
                    results["mcqs_created"] = created_count
            except Exception as e:
                print(f"Quiz generation failed: {e}")
                results["quiz_error"] = str(e)

            
        print(f"Generation complete for module {module.id}. Results: {results}")
        return Response({
            "status": "AI draft content generated",
            **results
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def get_drafts(self, request, pk=None):
        """View all unapproved questions and flashcards for this module."""
        module = self.get_object()
        
        # Flashcards
        decks = module.flashcard_decks.all()
        flashcards = Flashcard.objects.filter(deck__in=decks)
        
        # Questions linked directly to this module
        questions = Question.objects.filter(learning_module=module)
        
        return Response({
            "flashcards": FlashcardSerializer(flashcards, many=True).data,
            "questions": [
                {
                    "id": q.id, 
                    "text": q.question_text, 
                    "type": q.question_type,
                    "options": {
                        "A": q.option_a,
                        "B": q.option_b,
                        "C": q.option_c,
                        "D": q.option_d,
                    },
                    "correct_answer": q.correct_answer,
                    "explanation": q.explanation,
                    "is_approved": q.is_approved,
                    "confidence_score": q.ai_generation_metadata.first().confidence_score if q.ai_generation_metadata.exists() else None,
                    "difficulty": q.ai_generation_metadata.first().suggested_difficulty if q.ai_generation_metadata.exists() else q.difficulty_level
                } for q in questions
            ]
        })

    @action(detail=True, methods=['post'])
    def approve_item(self, request, pk=None):
        """Approve a specific flashcard or question."""
        item_type = request.data.get('item_type') # 'flashcard' or 'question'
        item_id = request.data.get('item_id')
        new_status = request.data.get('status') # Optional boolean
        
        if item_type == 'flashcard':
            item = get_object_or_404(Flashcard, id=item_id)
        else:
            item = get_object_or_404(Question, id=item_id)
            
        if new_status is not None:
            item.is_approved = bool(new_status)
        else:
            item.is_approved = not item.is_approved # Toggle if no status provided
            
        item.save()
        
        # Update AIGeneratedQuestion if applicable
        if item_type == 'question':
            AIGeneratedQuestion.objects.filter(question=item).update(is_approved=item.is_approved, reviewed_by=request.user)
            
        return Response({"status": "Item status updated", "is_approved": item.is_approved})

    @action(detail=True, methods=['post'])
    def edit_item(self, request, pk=None):
        """Update a specific flashcard or question."""
        item_type = request.data.get('item_type') # 'flashcard' or 'question'
        item_id = request.data.get('item_id')
        updates = request.data.get('updates', {})
        
        if item_type == 'flashcard':
            item = get_object_or_404(Flashcard, id=item_id)
            if 'front' in updates: item.front = updates['front']
            if 'back' in updates: item.back = updates['back']
        else:
            item = get_object_or_404(Question, id=item_id)
            if 'text' in updates: item.question_text = updates['text']
            if 'options' in updates:
                opts = updates['options']
                if 'A' in opts: item.option_a = opts['A']
                if 'B' in opts: item.option_b = opts['B']
                if 'C' in opts: item.option_c = opts['C']
                if 'D' in opts: item.option_d = opts['D']
            if 'correct_answer' in updates: item.correct_answer = updates['correct_answer']
            if 'explanation' in updates: item.explanation = updates['explanation']
            if 'model_answer' in updates: item.model_answer = updates['model_answer']
            if 'required_keywords' in updates: item.required_keywords = updates['required_keywords']
            
        item.save()
        return Response({"status": "Item updated", "item_id": item_id})

    @action(detail=True, methods=['post'])
    def delete_item(self, request, pk=None):
        """Permanently delete a draft flashcard or question."""
        item_type = request.data.get('item_type') # 'flashcard' or 'question'
        item_id = request.data.get('item_id')
        
        if item_type == 'flashcard':
            item = get_object_or_404(Flashcard, id=item_id)
        else:
            item = get_object_or_404(Question, id=item_id)
            
        item.delete()
        return Response({"status": "Item deleted", "item_id": item_id})

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Finalize the module and create assignments."""
        module = self.get_object()
        
        # 1. Ensure Quiz Assignment exists
        
        # 2. Assign to classroom (if not already handled by prerequisite logic)
        module.is_published = True
        module.save()
        
        # Publish Flashcard Decks
        module.flashcard_decks.update(is_published=True)
        
        # Create/Update Quiz Assignment
        approved_qs = Question.objects.filter(learning_module=module, is_approved=True)
        active_questions_count = approved_qs.count()
        
        summary = {
            "status": "Module published and content assigned",
            "flashcards_published": module.flashcard_decks.filter(is_published=True).count(),
            "questions_published": active_questions_count,
            "quiz_created": False
        }

        if active_questions_count > 0:
            from quiz.models import Quiz
            quiz, created = Quiz.objects.get_or_create(
                title=f"Assessment: {module.title}",
                created_by=request.user,
                defaults={'is_active': True, 'total_questions': min(active_questions_count, 10)}
            )
            summary["quiz_created"] = True
            summary["quiz_id"] = quiz.id
            
            if module.topic:
                quiz.topics.add(module.topic)
                
            from users.models import ClassroomQuizAssignment
            from django.utils import timezone
            import datetime
            
            ClassroomQuizAssignment.objects.get_or_create(
                quiz=quiz,
                classroom=module.classroom,
                defaults={
                    'prerequisite_module': module,
                    'is_active': True,
                    'due_date': timezone.now() + datetime.timedelta(days=7)
                }
            )
            
        return Response(summary)

    @action(detail=True, methods=['get'])
    def get_analytics(self, request, pk=None):
        """Get student progress summary for this module."""
        module = self.get_object()
        progress = module.student_progress.all()
        
        stats = {
            "not_started": progress.filter(status='not_started').count(),
            "in_progress": progress.filter(status='in_progress').count(),
            "completed": progress.filter(status='completed').count(),
            "total_students": module.classroom.students.count(),
            "student_details": []
        }
        
        # Add details for each student in the classroom
        for student in module.classroom.students.all():
            student_progress = progress.filter(student=student).first()
            stats["student_details"].append({
                "student_name": student.full_name or student.username,
                "status": student_progress.status if student_progress else 'not_started',
                "time_spent": student_progress.time_spent_seconds if student_progress else 0,
                "completion": student_progress.completion_percentage if student_progress else 0
            })
            
        return Response(stats)

class StudentModuleProgressViewSet(viewsets.ModelViewSet):
    """
    ViewSet for tracking student progress.
    Teachers can view all progress for their modules.
    Students can view and update their own progress.
    """
    serializer_class = StudentModuleProgressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'teacher':
            return StudentModuleProgress.objects.filter(module__classroom__teacher=user)
        return StudentModuleProgress.objects.filter(student=user)

    @action(detail=False, methods=['post'], url_path='update-progress')
    def update_progress(self, request):
        """
        Student updates their progress for a specific module.
        Expected data: module_id, time_spent (seconds), status (optional)
        """
        module_id = request.data.get('module_id')
        time_spent = request.data.get('time_spent', 0)
        status_val = request.data.get('status')
        
        if not module_id:
            return Response({"error": "module_id required"}, status=status.HTTP_400_BAD_REQUEST)

        module = get_object_or_404(LearningModule, id=module_id)
        
        progress, created = StudentModuleProgress.objects.get_or_create(
            student=request.user,
            module=module
        )
        
        if time_spent:
            progress.time_spent_seconds += int(time_spent)
        
        if status_val:
            progress.status = status_val
            if status_val == 'completed':
                progress.completion_percentage = 100.0
            elif status_val == 'in_progress' and progress.completion_percentage == 0:
                 progress.completion_percentage = 10.0 # Started
        
        progress.save()
        return Response(StudentModuleProgressSerializer(progress).data)

class FlashcardDeckViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FlashcardDeckSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return FlashcardDeck.objects.all()
