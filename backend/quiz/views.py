from rest_framework import viewsets, status, permissions # reload trigger
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Topic, Subtopic, Question, Quiz, QuizSession, Response as QuizResponse, QuizResetLog
from users.models import User, Classroom
from .serializers import (
    TopicSerializer, SubtopicSerializer, QuestionSerializer,
    QuestionListSerializer, QuestionDetailSerializer, QuizSerializer,
    QuizSessionSerializer, QuizSessionCreateSerializer,
    ResponseSerializer, ResponseSubmitSerializer
)
from rest_framework.pagination import PageNumberPagination
import random


class TopicViewSet(viewsets.ModelViewSet):
    """CRUD operations for Topics"""
    queryset = Topic.objects.all()
    serializer_class = TopicSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            # Allow teachers and admin users to manage topics
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]
    
    def perform_create(self, serializer):
        # Only allow teachers and staff to create topics
        if self.request.user.role != 'teacher' and not self.request.user.is_staff:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only teachers can create topics")
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        # Allow any teacher or staff member to update topics
        if self.request.user.role != 'teacher' and not self.request.user.is_staff:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only teachers can edit topics")
        serializer.save()
    
    def perform_destroy(self, instance):
        # Allow any teacher or staff member to delete topics
        if self.request.user.role != 'teacher' and not self.request.user.is_staff:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only teachers can delete topics")
        instance.delete()
    
    @action(detail=True, methods=['get'], url_path='subtopics')
    def subtopics(self, request, pk=None):
        """Get all subtopics for a specific topic"""
        topic = self.get_object()
        subtopics = topic.subtopics.all()
        serializer = SubtopicSerializer(subtopics, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='duplicate')
    def duplicate_topic(self, request, pk=None):
        """Duplicate a topic with all its subtopics and questions"""
        if request.user.role != 'teacher' and not request.user.is_staff:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only teachers can duplicate topics")
        
        original_topic = self.get_object()
        new_name = request.data.get('name', f"{original_topic.name} (Copy)")
        
        # Check if name already exists
        if Topic.objects.filter(name=new_name).exists():
            return Response(
                {'error': f'Topic with name "{new_name}" already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create duplicate topic
        new_topic = Topic.objects.create(
            name=new_name,
            description=original_topic.description,
            created_by=request.user
        )
        
        # Duplicate subtopics
        subtopic_mapping = {}
        for subtopic in original_topic.subtopics.all():
            new_subtopic = Subtopic.objects.create(
                topic=new_topic,
                name=subtopic.name,
                description=subtopic.description
            )
            subtopic_mapping[subtopic.id] = new_subtopic
        
        # Duplicate questions
        questions_created = 0
        for question in Question.objects.filter(topic=original_topic):
            new_question = Question.objects.create(
                topic=new_topic,
                subtopic=subtopic_mapping.get(question.subtopic_id) if question.subtopic_id else None,
                question_text=question.question_text,
                option_a=question.option_a,
                option_b=question.option_b,
                option_c=question.option_c,
                option_d=question.option_d,
                correct_answer=question.correct_answer,
                difficulty_level=question.difficulty_level,
                explanation=question.explanation,
                image=question.image,
                irt_difficulty=question.irt_difficulty,
                irt_discrimination=question.irt_discrimination,
                created_by=request.user
            )
            questions_created += 1
        
        return Response({
            'message': 'Topic duplicated successfully',
            'new_topic': TopicSerializer(new_topic).data,
            'subtopics_created': len(subtopic_mapping),
            'questions_created': questions_created
        }, status=status.HTTP_201_CREATED)


class SubtopicViewSet(viewsets.ModelViewSet):
    """CRUD operations for Subtopics"""
    queryset = Subtopic.objects.all()
    serializer_class = SubtopicSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = Subtopic.objects.all()
        topic_id = self.request.query_params.get('topic', None)
        if topic_id:
            queryset = queryset.filter(topic_id=topic_id)
        return queryset
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]
    
    def perform_create(self, serializer):
        if self.request.user.role != 'teacher' and not self.request.user.is_staff:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only teachers can create subtopics")
        serializer.save()
    
    @action(detail=True, methods=['get'], url_path='questions')
    def questions(self, request, pk=None):
        """Get all questions for a specific subtopic"""
        subtopic = self.get_object()
        questions = subtopic.questions.all()
        from .serializers import QuestionListSerializer
        serializer = QuestionListSerializer(questions, many=True)
        return Response(serializer.data)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 1000

class QuestionViewSet(viewsets.ModelViewSet):
    """CRUD operations for Questions"""
    queryset = Question.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return QuestionListSerializer
        return QuestionSerializer
    
    
    
    pagination_class = StandardResultsSetPagination


    
    def get_queryset(self):
        queryset = Question.objects.all()
        
        # Filter by topic
        topic_id = self.request.query_params.get('topic', None)
        if topic_id:
            queryset = queryset.filter(topic_id=topic_id)
        
        # Filter by subtopic
        subtopic_id = self.request.query_params.get('subtopic', None)
        if subtopic_id:
            queryset = queryset.filter(subtopic_id=subtopic_id)
        
        # Filter by difficulty
        difficulty = self.request.query_params.get('difficulty', None)
        if difficulty:
            queryset = queryset.filter(difficulty_level=difficulty)

        # Filter by question_type
        q_type = self.request.query_params.get('question_type', None)
        if q_type:
            queryset = queryset.filter(question_type=q_type)
            
        # Filter by search term
        search_query = self.request.query_params.get('search', None)
        if search_query:
            queryset = queryset.filter(question_text__icontains=search_query)

        # Filter by specific IDs
        ids = self.request.query_params.get('ids', None)
        if ids:
            id_list = ids.split(',')
            queryset = queryset.filter(id__in=id_list)
        
        return queryset
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]
    
    def perform_create(self, serializer):
        if self.request.user.role != 'teacher' and not self.request.user.is_staff:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only teachers can create questions")
            
        # Check for duplicates
        topic = serializer.validated_data.get('topic')
        question_text = serializer.validated_data.get('question_text')
        if Question.objects.filter(topic=topic, question_text=question_text).exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"detail": "This question already exists in this topic."})
            
        serializer.save()
    
    @action(detail=False, methods=['post'], url_path='bulk-upload')
    def bulk_upload(self, request):
        """Bulk upload questions from CSV or Excel file"""
        import csv
        import io
        import openpyxl
        
        if 'file' not in request.FILES:
            return Response({
                'error': 'No file provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        file = request.FILES['file']
        is_excel = file.name.endswith('.xlsx')
        is_csv = file.name.endswith('.csv')
        
        # Validate file type
        if not (is_excel or is_csv):
            return Response({
                'error': 'File must be CSV or Excel (.xlsx)'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Parse data
            data_rows = []
            
            if is_excel:
                wb = openpyxl.load_workbook(file)
                sheet = wb.active
                
                # Get headers
                headers = [cell.value for cell in sheet[1]]
                
                # Iterate rows
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    # Skip empty rows
                    if not any(row):
                        continue
                        
                    # Map to dictionary
                    row_dict = {}
                    for i, header in enumerate(headers):
                        if i < len(row) and header:
                            row_dict[str(header).strip()] = row[i]
                    data_rows.append(row_dict)
            else:
                # Read CSV
                decoded_file = file.read().decode('utf-8')
                csv_reader = csv.DictReader(io.StringIO(decoded_file))
                data_rows = list(csv_reader)
            
            # Get all topics for validation
            topics_dict = {topic.name: topic for topic in Topic.objects.all()}
            
            created_count = 0
            skipped_count = 0
            errors = []
            
            for row_num, row in enumerate(data_rows, start=2):
                try:
                    # Normalize keys (lowercase) and map aliases
                    # Create a new normalized row
                    norm_row = {}
                    
                    # Column Mapping
                    ws_map = {
                        'topic': 'topic_name',
                        'question': 'question_text',
                        'difficulty': 'difficulty_level',
                        'correct answer': 'correct_answer',
                        'answer': 'correct_answer',
                        'explanation': 'explanation',
                        'right answer': 'correct_answer',
                    }
                    
                    for k, v in row.items():
                        if not k: continue
                        k_lower = str(k).strip().lower()
                        
                        # Direct match or mapped match
                        if k_lower in ws_map:
                            norm_row[ws_map[k_lower]] = v
                        elif k_lower.startswith('option'):
                            # Handle Option A, Option B etc.
                            opt_char = k_lower.replace('option', '').strip().lower()
                            if opt_char in ['a', 'b', 'c', 'd']:
                                norm_row[f'option_{opt_char}'] = v
                            else:
                                norm_row[k_lower] = v # formatting like "option_a" already?
                        else:
                            norm_row[k_lower.replace(' ', '_')] = v
                            
                    row = norm_row
                    
                    # Validate required fields common to all
                    # Validate required fields common to all
                    # Validate required fields common to all
                    common_required = ['question_text', 'topic_name', 'difficulty_level']
                    
                    missing = []
                    for f in common_required:
                        if f not in row or (row[f] is None) or (str(row[f]).strip() == ''):
                            missing.append(f)
                    
                    if missing:
                        errors.append(f"Row {row_num}: Missing fields: {', '.join(missing)}")
                        continue

                    # Determine question type
                    q_type = str(row.get('question_type', 'mcq')).strip().lower()
                    if q_type not in ['mcq', 'short_answer', 'essay']:
                        q_type = 'mcq' # Default to MCQ if invalid or missing

                    # Type-specific validation
                    correct = ''
                    if q_type == 'mcq':
                        mcq_required = ['option_a', 'option_b', 'option_c', 'option_d', 'correct_answer']
                        for f in mcq_required:
                            if f not in row or (row[f] is None) or (str(row[f]).strip() == ''):
                                missing.append(f)
                        
                        if missing:
                            errors.append(f"Row {row_num}: Missing MCQ fields: {', '.join(missing)}")
                            continue
                            
                        # Validate correct_answer for MCQ
                        correct = str(row['correct_answer']).strip().upper()
                        if correct not in ['A', 'B', 'C', 'D']:
                            errors.append(f"Row {row_num}: Invalid correct_answer '{correct}'")
                            continue
                            
                    elif q_type in ['short_answer', 'essay']:
                        # Optional: Validate model_answer presence?
                        # For now, let's make it optional or warning
                        pass
                    
                    # Validate topic exists or create it
                    topic_name = str(row['topic_name']).strip()
                    if topic_name not in topics_dict:
                        # Create new topic
                        try:
                            new_topic = Topic.objects.create(
                                name=topic_name,
                                created_by=request.user,
                                description=f"Auto-created during bulk upload"
                            )
                            topics_dict[topic_name] = new_topic
                        except Exception as e:
                            errors.append(f"Row {row_num}: Failed to create topic '{topic_name}'")
                            continue
                    
                    # Validate subtopic (optional)
                    subtopic = None
                    subtopic_name = str(row.get('subtopic', '') or row.get('subtopic_name', '') or '').strip()
                    if subtopic_name:
                        subtopic = Subtopic.objects.filter(topic=topics_dict[topic_name], name__iexact=subtopic_name).first()
                        if not subtopic:
                            try:
                                subtopic = Subtopic.objects.create(
                                    topic=topics_dict[topic_name],
                                    name=subtopic_name,
                                    description="Auto-created during bulk upload"
                                )
                            except Exception as e:
                                errors.append(f"Row {row_num}: Failed to create subtopic '{subtopic_name}'")
                                continue
                    
                    # Validate difficulty
                    try:
                        difficulty = int(row['difficulty_level'])
                        if difficulty < 1 or difficulty > 5:
                            raise ValueError()
                    except:
                        errors.append(f"Row {row_num}: Invalid difficulty_level")
                        continue
                    
                    # Check for duplicates
                    q_text = str(row['question_text']).strip()
                    if Question.objects.filter(topic=topics_dict[topic_name], question_text=q_text).exists():
                        skipped_count += 1
                        continue

                    # Create question
                    common_data = {
                        'topic': topics_dict[topic_name],
                        'subtopic': subtopic,
                        'question_text': q_text,
                        'question_type': q_type,
                        'difficulty_level': difficulty,
                        'explanation': str(row.get('explanation', '') or '').strip()
                    }
                    
                    if q_type == 'mcq':
                        Question.objects.create(
                            **common_data,
                            option_a=str(row['option_a']).strip(),
                            option_b=str(row['option_b']).strip(),
                            option_c=str(row['option_c']).strip(),
                            option_d=str(row['option_d']).strip(),
                            correct_answer=correct
                        )
                    else:
                        # For text questions
                        Question.objects.create(
                            **common_data,
                            model_answer=str(row.get('model_answer', '') or '').strip(),
                            # Default empty options for non-MCQ to match model constraints if any (we made them blank=True)
                        )
                        
                    created_count += 1

                    
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
            
            return Response({
                'message': f'Imported {created_count} questions. Skipped {skipped_count} duplicates.',
                'created_count': created_count,
                'skipped_count': skipped_count,
                'errors': errors if errors else None
            }, status=status.HTTP_201_CREATED if created_count > 0 else status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                'error': f'Failed to process file: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


class QuizViewSet(viewsets.ModelViewSet):
    """CRUD operations for Quizzes"""
    queryset = Quiz.objects.all()
    serializer_class = QuizSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        if self.request.user.role != 'teacher' and not self.request.user.is_staff:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only teachers can create quizzes")
        serializer.save(created_by=self.request.user)
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]
    
    def list(self, request, *args, **kwargs):
        """List quizzes with session cleanup"""
        # Clean up old sessions (> 24 hours)
        if request.user.is_authenticated:
            from django.utils import timezone
            import datetime
            from .models import QuizSession
            
            expire_time = timezone.now() - datetime.timedelta(hours=24)
            QuizSession.objects.filter(
                user=request.user, 
                is_active=True, 
                started_at__lt=expire_time
            ).update(is_active=False)
            
        return super().list(request, *args, **kwargs)

    @action(detail=True, methods=['get'])
    def export_results_csv(self, request, pk=None):
        """Export all results for a quiz as CSV"""
        quiz = self.get_object()
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{quiz.title}_results.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Student Name', 'Email', 'Score', 'Accuracy', 'Mindset', 'Behavior Score', 'AI Suggestion', 'Time Taken (min)', 'Date', 'Attempt'])
        
        # Get completed sessions
        from .models import QuizSession
        sessions = QuizSession.objects.filter(quiz=quiz, is_active=False).select_related('user').order_by('-completed_at')
        
        for session in sessions:
            if not session.user:
                continue
                
            total_q = session.correct_answers + session.incorrect_answers
            accuracy = (session.correct_answers / total_q * 100) if total_q > 0 else 0
            time_taken = session.accumulated_time / 60 if session.accumulated_time else 0
            
            # Generate AI Suggestion
            suggestions = []
            if session.behavior_score < 70:
                suggestions.append("Improve focus")
            if accuracy < 60:
                suggestions.append("Review concepts")
            elif accuracy > 90:
                suggestions.append("Try advanced quiz")
            
            if session.detected_mindset in ['anxious', 'frustrated']:
                suggestions.append("Take breaks")
            
            ai_suggestion = "; ".join(suggestions) if suggestions else "Maintain consistency"
            
            writer.writerow([
                session.user.profile.full_name if hasattr(session.user, 'profile') else session.user.username,
                session.user.email,
                f"{session.total_score:.1f}",
                f"{accuracy:.1f}%",
                session.detected_mindset.capitalize(),
                f"{session.behavior_score:.1f}",
                ai_suggestion,
                f"{time_taken:.1f}",
                session.completed_at.strftime('%Y-%m-%d %H:%M') if session.completed_at else '',
                session.attempt_number
            ])
            
        return response
    
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """Assign quiz to a classroom"""
        quiz = self.get_object()
        classroom_id = request.data.get('classroom_id')
        
        if not classroom_id:
            return Response({
                'error': 'classroom_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        from users.models import Classroom
        try:
            classroom = Classroom.objects.get(id=classroom_id)
        except Classroom.DoesNotExist:
            return Response({
                'error': 'Classroom not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'message': f'Quiz "{quiz.title}" assigned to classroom "{classroom.name}"',
            'quiz_id': str(quiz.id),
            'classroom_id': str(classroom.id)
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='export_all_results_csv')
    def export_all_results_csv(self, request):
        """Export aggregated results for ALL quizzes as CSV"""
        if getattr(request.user, 'role', '') != 'teacher' and not request.user.is_staff:
             from rest_framework.exceptions import PermissionDenied
             raise PermissionDenied("Only teachers can export results")

        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="all_quizzes_results.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Student Name', 'Email', 'Quiz Title', 'Score', 'Accuracy', 'Mindset', 'Behavior Score', 'AI Suggestion', 'Time Taken (min)', 'Date', 'Attempt'])
        
        from .models import QuizSession
        quizzes = Quiz.objects.filter(created_by=request.user)
        sessions = QuizSession.objects.filter(quiz__in=quizzes, is_active=False).select_related('user', 'quiz').order_by('-completed_at')
        
        for session in sessions:
            if not session.user:
                continue
                
            total_q = session.correct_answers + session.incorrect_answers
            accuracy = (session.correct_answers / total_q * 100) if total_q > 0 else 0
            time_taken = session.accumulated_time / 60 if session.accumulated_time else 0
            
            # Generate AI Suggestion
            suggestions = []
            if session.behavior_score < 70:
                suggestions.append("Improve focus and reduce tab switching")
            if accuracy < 60:
                suggestions.append("Review fundamental concepts")
            elif accuracy > 90:
                suggestions.append("Ready for advanced topics")
            
            if session.detected_mindset in ['anxious', 'frustrated', 'confused']:
                suggestions.append(f"Address {session.detected_mindset} mindset with breaks")
            
            ai_suggestion = "; ".join(suggestions) if suggestions else "Maintain consistency"

            writer.writerow([
                session.user.get_full_name() or session.user.username,
                session.user.email,
                session.quiz.title,
                f"{session.total_score:.1f}",
                f"{accuracy:.1f}%",
                session.detected_mindset.capitalize(),
                f"{session.behavior_score:.1f}",
                ai_suggestion,
                f"{time_taken:.1f}",
                session.completed_at.strftime('%Y-%m-%d %H:%M') if session.completed_at else '',
                session.attempt_number
            ])
            
        return response

    @action(detail=False, methods=['get'], url_path='all_student_results')
    def all_student_results(self, request):
        """Get all student results for ALL quizzes created by the current user"""
        
        # Only teachers can access this
        if getattr(request.user, 'role', '') != 'teacher' and not request.user.is_staff:
             return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)

        # Get all quizzes created by user or classroom filter
        from .models import QuizSession
        from django.db.models import Q
        
        classroom_id = request.query_params.get('classroom_id')
        if classroom_id:
            from users.models import Classroom
            if not Classroom.objects.filter(id=classroom_id).filter(Q(teacher=request.user) | Q(co_teachers=request.user)).exists():
                 return Response({'error': 'Unauthorized access to classroom'}, status=status.HTTP_403_FORBIDDEN)
            sessions = QuizSession.objects.filter(classroom_assignment__classroom_id=classroom_id, is_active=False)
        else:
            # Include: 
            # 1. Quizzes created by the user
            # 2. Sessions linked to classrooms where the user is a teacher or co-teacher
            from users.models import Classroom
            teacher_classrooms = Classroom.objects.filter(Q(teacher=request.user) | Q(co_teachers=request.user))
            
            sessions = QuizSession.objects.filter(
                Q(quiz__created_by=request.user) | 
                Q(classroom_assignment__classroom__in=teacher_classrooms),
                is_active=False
            )
        
        sessions = sessions.select_related('user', 'quiz').order_by('-completed_at')
        
        results_data = []
        for session in sessions:
            time_taken = 0
            if session.completed_at and session.started_at:
                diff = session.completed_at - session.started_at
                time_taken = diff.total_seconds() / 60
                
            results_data.append({
                'session_id': session.id,
                'student_id': session.user.id,
                'student_name': session.user.get_full_name() or session.user.username,
                'student_email': session.user.email,
                'quiz_title': session.quiz.title,
                'quiz_id': str(session.quiz.id),
                'score': session.total_score,
                'accuracy': session.accuracy,
                'time_spent': time_taken,
                'behavior_score': session.behavior_score,
                'completed_at': session.completed_at,
                'attempt_number': session.attempt_number
            })
            
        return Response(results_data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='student_results')
    def student_results(self, request, pk=None):
        """Get all student results for a specific quiz"""
        quiz = self.get_object()
        
        # Determine permissions: Teacher (creator), Staff, OR teacher of an assigned classroom
        is_creator = quiz.created_by == request.user
        
        from users.models import Classroom
        is_teacher_of_assigned_class = Classroom.objects.filter(
            Q(teacher=request.user) | Q(co_teachers=request.user),
            assigned_quizzes__quiz=quiz
        ).exists()
        
        if not (is_creator or is_teacher_of_assigned_class or request.user.is_staff):
             return Response({
                'error': 'You do not have permission to view results for this quiz'
            }, status=status.HTTP_403_FORBIDDEN)
            
        sessions = QuizSession.objects.filter(quiz=quiz, is_active=False).select_related('user')
        
        results_data = []
        for session in sessions:
            # Calculate time taken in minutes
            time_taken = 0
            if session.completed_at and session.started_at:
                diff = session.completed_at - session.started_at
                time_taken = diff.total_seconds() / 60
                
            results_data.append({
                'session_id': session.id,
                'student_id': session.user.id,  # Added for reset functionality
                'student_name': session.user.get_full_name() or session.user.username,
                'student_email': session.user.email,
                'score': session.total_score,
                'accuracy': session.accuracy, # using the property from model/serializer
                'time_taken': time_taken,
                'behavior_score': session.behavior_score,
                'completed_at': session.completed_at,
                'attempt_number': session.attempt_number
            })
            
        return Response(results_data, status=status.HTTP_200_OK)


class QuizSessionViewSet(viewsets.ModelViewSet):
    """Manage quiz sessions"""
    queryset = QuizSession.objects.all()
    serializer_class = QuizSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        classroom_id = self.request.query_params.get('classroom_id')
        qs = QuizSession.objects.all()
        # Students: only their own sessions
        if getattr(user, 'role', None) == 'student':
            qs = qs.filter(user=user)
        # Teachers: sessions for their classrooms or quizzes they created
        elif getattr(user, 'role', None) == 'teacher':
            from users.models import Classroom
            from django.db.models import Q
            teacher_classrooms = Classroom.objects.filter(Q(teacher=user) | Q(co_teachers=user))
            classroom_ids = teacher_classrooms.values_list('id', flat=True)
            qs = qs.filter(
                Q(classroom_assignment__classroom_id__in=classroom_ids) |
                Q(quiz__created_by=user)
            )
        # Staff: can see all
        elif user.is_staff:
            pass  # no filter
        else:
            # Default fallback: only own sessions
            qs = qs.filter(user=user)
        if classroom_id:
            qs = qs.filter(classroom_assignment__classroom_id=classroom_id)
        return qs.order_by('-started_at')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return QuizSessionCreateSerializer
        return QuizSessionSerializer
    
    def create(self, request, *args, **kwargs):
        """Create a new quiz session with retake validation"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        quiz_id = serializer.validated_data.get('quiz').id
        quiz = Quiz.objects.get(id=quiz_id)
        
        # Check previous attempts
        previous_attempts = QuizSession.objects.filter(
            user=request.user,
            quiz=quiz
        ).count()
        
        # Validate retakes
        if previous_attempts > 0:
            if not quiz.allow_retakes:
                return Response(
                    {"error": "Retakes are not allowed for this quiz"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            if previous_attempts >= quiz.max_attempts:
                return Response(
                    {"error": f"Maximum {quiz.max_attempts} attempts reached for this quiz"},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Create the session with attempt number
        from django.utils import timezone
        from users.models import ClassroomQuizAssignment
        from learning.models import StudentModuleProgress

        # CHECK FOR GATING LOGIC (Prerequisite Modules)
        # Find if this quiz is assigned to the user via any classroom
        # We check all assignments for this quiz where the classroom has this student
        active_assignments = ClassroomQuizAssignment.objects.filter(
            quiz=quiz,
            classroom__students=request.user,
            is_active=True
        )

        for assignment in active_assignments:
            if assignment.prerequisite_module:
                # Check if student has completed the module
                try:
                    progress = StudentModuleProgress.objects.get(
                        student=request.user,
                        module=assignment.prerequisite_module
                    )
                    if progress.status != 'completed':
                        return Response(
                            {
                                "error": "You must complete the learning module before taking this quiz.",
                                "prerequisite_module_id": assignment.prerequisite_module.id,
                                "prerequisite_module_title": assignment.prerequisite_module.title
                            },
                            status=status.HTTP_403_FORBIDDEN
                        )
                except StudentModuleProgress.DoesNotExist:
                    return Response(
                        {
                            "error": "You must start and complete the learning module before taking this quiz.",
                            "prerequisite_module_id": assignment.prerequisite_module.id,
                            "prerequisite_module_title": assignment.prerequisite_module.title
                        },
                        status=status.HTTP_403_FORBIDDEN
                    )

        session = serializer.save(
            user=request.user,
            attempt_number=previous_attempts + 1,
            started_at=timezone.now(),
            last_activity_at=timezone.now(),
            accumulated_time=0.0,
            # Link to the first valid assignment found (optional but good for tracking)
            classroom_assignment=active_assignments.first()
        )
        
        # Return full session data
        return Response(QuizSessionSerializer(session).data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def next_question(self, request, pk=None):
        """
        Get the next adaptive question for the quiz session.
        Uses IRT-based difficulty adjustment.
        """
        session = self.get_object()
        
        # Check if quiz is inactive or completed
        if not session.is_active or session.current_question_index >= session.quiz.total_questions:
            return Response({
                'message': 'Quiz completed',
                'completed': True,
                'session_id': session.id
            }, status=status.HTTP_200_OK)
        
        # Get questions from quiz topics
        quiz_topics = session.quiz.topics.all()
        if quiz_topics.exists():
            available_questions = Question.objects.filter(topic__in=quiz_topics)
        else:
            # Fallback for quizzes without topics (e.g. Diagnostic)
            available_questions = Question.objects.all()
        
        # Exclude already answered questions
        answered_question_ids = session.responses.values_list('question_id', flat=True)
        available_questions = available_questions.exclude(id__in=answered_question_ids)
        
        # Filter by current difficulty level (±1 level for variety)
        difficulty_range = [
            max(1, session.current_difficulty_level - 1),
            min(5, session.current_difficulty_level + 1)
        ]
        available_questions = available_questions.filter(
            difficulty_level__in=difficulty_range
        )
        
        if not available_questions.exists():
            # If no questions at this difficulty, get any available question
            available_questions = Question.objects.filter(
                topic__in=quiz_topics
            ).exclude(id__in=answered_question_ids)
        
        if not available_questions.exists():
            return Response({
                'error': 'No more questions available'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Select question based on shuffling and adaptive settings
        should_shuffle = True
        if session.classroom_assignment:
            should_shuffle = session.classroom_assignment.shuffle_questions
        
        if session.quiz.is_adaptive or should_shuffle:
            question = random.choice(available_questions)
        else:
            # Pick the "first" available question for consistent order
            question = available_questions.order_by('created_at', 'id').first()
        
        # Update last activity for resume logic
        from django.utils import timezone
        session.last_activity_at = timezone.now()
        session.save(update_fields=['last_activity_at'])
        
        # Calculate virtual start time based on accumulated time
        import datetime
        virtual_start_time = timezone.now() - datetime.timedelta(seconds=session.accumulated_time)
        
        # Get proctoring settings
        enable_proctoring = True  # TEMPORARY: Enable for testing (change to False for production)
        strict_time_limit = True  # TEMPORARY: Enable for testing
        if session.classroom_assignment:
            enable_proctoring = session.classroom_assignment.enable_proctoring
            strict_time_limit = session.classroom_assignment.strict_time_limit

        return Response({
            'question': QuestionDetailSerializer(question).data,
            'question_number': session.current_question_index + 1,
            'total_questions': session.quiz.total_questions,
            'current_difficulty': session.current_difficulty_level,
            'student_ability': session.student_ability,
            'detected_mindset': session.detected_mindset or 'neutral',
            'quiz_title': session.quiz.title,  # Add quiz title for display
            'time_limit': session.quiz.time_limit,  # Add time limit in minutes
            'quiz_started_at': virtual_start_time.isoformat(),  # Virtual start time for frontend timer
            'show_answers': session.quiz.show_answers,
            'show_explanations': session.quiz.show_explanations,
            'show_answers_immediately': session.quiz.show_answers,  # For immediate feedback
            'enable_proctoring': enable_proctoring,
            'strict_time_limit': strict_time_limit,
            # Proctoring state persistence
            'fullscreen_violations': session.total_fullscreen_violations,
            'no_face_violations': session.total_no_face_violations,
            'tab_switches': session.total_tab_switches
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def log_violation(self, request, pk=None):
        """Log a proctoring violation immediately"""
        session = self.get_object()
        violation_type = request.data.get('type')
        
        if violation_type == 'fullscreen':
            session.total_fullscreen_violations += 1
        elif violation_type == 'no_face':
            session.total_no_face_violations += 1
        elif violation_type == 'tab_switch':
            session.total_tab_switches += 1
            
        session.save()
        
        return Response({
            'status': 'logged',
            'fullscreen_violations': session.total_fullscreen_violations,
            'no_face_violations': session.total_no_face_violations,
            'tab_switches': session.total_tab_switches
        })

    @action(detail=True, methods=['get'], url_path='download-report')
    def download_report(self, request, pk=None):
        """Generate and download PDF report"""
        session = self.get_object()
        
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            import io
            from django.http import HttpResponse
        except ImportError:
            return Response(
                {"error": "PDF generation library not installed. Please run: pip install reportlab"},
                status=status.HTTP_501_NOT_IMPLEMENTED
            )

        # Create PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        styles = getSampleStyleSheet()
        story = []

        # Title
        title_style = styles["Heading1"]
        title_style.alignment = 1 # Center
        story.append(Paragraph("Adaptive AI Quiz Report", title_style))
        story.append(Spacer(1, 12))
        story.append(Paragraph(session.quiz.title, styles["Heading2"]))
        story.append(Spacer(1, 24))

        # Student Info
        student_name = session.user.get_full_name() or session.user.username
        accuracy_text = f"{session.accuracy:.1f}%" if session.accuracy is not None else "N/A"
        
        info_data = [
            ["Student Name:", student_name],
            ["Date Taken:", session.started_at.strftime("%Y-%m-%d %H:%M")],
            ["Attempt Number:", str(session.attempt_number)],
            ["Behavior Score:", f"{session.behavior_score:.0f}/100"],
            ["Accuracy:", accuracy_text]
        ]
        
        t = Table(info_data, colWidths=[2*inch, 3*inch])
        t.setStyle(TableStyle([
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 12),
        ]))
        story.append(t)
        story.append(Spacer(1, 24))

        # Insights
        if session.detected_mindset:
            story.append(Paragraph("AI Insights", styles["Heading3"]))
            story.append(Paragraph(f"Detected Mindset: {session.detected_mindset.title()}", styles["Normal"]))
            story.append(Spacer(1, 12))

        # Build
        try:
            doc.build(story)
        except Exception as e:
             return Response({"error": f"Failed to generate PDF: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="quiz_report_{session.id}.pdf"'
        return response
    
    @action(detail=True, methods=['post'])
    def submit_answer(self, request, pk=None):
        """
        Submit an answer and get adaptive feedback.
        Updates difficulty based on performance.
        """
        session = self.get_object()
        
        if not session.is_active:
            return Response({
                'error': 'Quiz session is not active'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = ResponseSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        question = get_object_or_404(Question, id=serializer.validated_data['question_id'])
        
        # Create response
        response = QuizResponse.objects.create(
            session=session,
            question=question,
            selected_answer=serializer.validated_data.get('selected_answer', ''),
            response_time=serializer.validated_data['response_time'],
            hesitation_count=serializer.validated_data['hesitation_count'],
            tab_switches=serializer.validated_data['tab_switches'],
            question_difficulty_at_time=session.current_difficulty_level
        )
        
        # Update session statistics
        # For MCQ, is_correct is calculated in save()
        response.refresh_from_db()
                
        if response.is_correct:
            session.correct_answers += 1
            # Increase difficulty if answer is correct and confidence is high
            if response.confidence_level > 0.7:
                session.current_difficulty_level = min(5, session.current_difficulty_level + 1)
        else:
            session.incorrect_answers += 1
            # Decrease difficulty if answer is incorrect
            session.current_difficulty_level = max(1, session.current_difficulty_level - 1)
        
        # Update IRT ability estimate (simplified)
        if response.is_correct:
            session.student_ability += 0.2
        else:
            session.student_ability -= 0.2
        
        # Update accumulated time
        from django.utils import timezone
        now = timezone.now()
        if session.last_activity_at:
            time_spent = (now - session.last_activity_at).total_seconds()
            # Only count reasonable active time (e.g. ignore if > 1 hour gap which implies disconnected pause)
            # But effectively we trust the sequence get_next_question -> submit_answer
            session.accumulated_time += time_spent
        
        session.last_activity_at = now
        
        # Update behavior tracking
        session.total_tab_switches += response.tab_switches
        session.total_hesitations += response.hesitation_count
        
        # Update average response time
        total_responses = session.responses.count()
        # Recalculate robustly or just incremental update
        session.avg_response_time = (session.avg_response_time * (total_responses - 1) + response.response_time) / total_responses
        
        # Update question index
        session.current_question_index += 1
        
        # Update question statistics
        question.times_asked += 1
        if response.is_correct:
            question.times_correct += 1
        question.save()
        
        session.save()
        
        # Send real-time WebSocket updates (optional - channels may not be installed)
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            channel_layer = get_channel_layer()
            if channel_layer:
                room_group_name = f'quiz_{session.id}'
                
                # Send answer feedback
                async_to_sync(channel_layer.group_send)(
                    room_group_name,
                    {
                        'type': 'answer_feedback',
                        'is_correct': response.is_correct,
                        'correct_answer': question.correct_answer,
                        'explanation': question.explanation,
                        'new_ability': session.student_ability
                    }
                )
            
                # Send difficulty update if changed
                async_to_sync(channel_layer.group_send)(
                    room_group_name,
                    {
                        'type': 'difficulty_update',
                        'difficulty': session.current_difficulty_level,
                        'reason': 'Correct answer' if response.is_correct else 'Incorrect answer'
                    }
                )
                
                # Send score update
                total = session.correct_answers + session.incorrect_answers
                accuracy = (session.correct_answers / total * 100) if total > 0 else 0
                async_to_sync(channel_layer.group_send)(
                    room_group_name,
                    {
                        'type': 'score_update',
                        'score': accuracy,
                        'correct': session.correct_answers,
                        'incorrect': session.incorrect_answers,
                        'accuracy': accuracy
                    }
                )
        except ImportError:
            pass  # channels not installed, skip WebSocket updates
        except Exception as e:
            print(f"WebSocket update failed: {e}")
        
        # Determine the correct answer text to return
        correct_answer_text = question.correct_answer
        if question.question_type in ['short_answer', 'essay']:
            correct_answer_text = question.model_answer

        return Response({
            'response': ResponseSerializer(response).data,
            'is_correct': response.is_correct,
            'correct_answer': correct_answer_text,
            'explanation': question.explanation,
            'show_feedback': session.quiz.show_answers,  # Show feedback if quiz allows
            'new_difficulty': session.current_difficulty_level,
            'student_ability': session.student_ability,
            'progress': {
                'current': session.current_question_index,
                'total': session.quiz.total_questions,
                'correct': session.correct_answers,
                'incorrect': session.incorrect_answers
            }
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete the quiz session and calculate final scores"""
        from django.utils import timezone
        
        session = self.get_object()
        
        if not session.is_active:
            # Idempotent: if already completed, just return success/results
            return Response({
                'message': 'Quiz session is already completed',
                'session_id': str(session.id),
                'total_score': session.total_score
            }, status=status.HTTP_200_OK)
        
        # Calculate final scores
        total_questions = session.correct_answers + session.incorrect_answers
        if total_questions > 0:
            accuracy = (session.correct_answers / total_questions) * 100
            session.total_score = accuracy
            
            # Calculate behavior score (0-100)
            # Lower tab switches and hesitations = higher score
            tab_penalty = min(session.total_tab_switches * 2, 30)
            hesitation_penalty = min(session.total_hesitations, 20)
            time_bonus = 10 if session.avg_response_time < 15 else 0
            
            session.behavior_score = max(0, 100 - tab_penalty - hesitation_penalty + time_bonus)
        
        # Detect mindset based on behavior
        if session.avg_response_time < 10 and session.total_hesitations < 5:
            session.detected_mindset = 'confident'
        elif session.total_hesitations > 15 or session.avg_response_time > 30:
            session.detected_mindset = 'confused'
        elif session.total_tab_switches > 10:
            session.detected_mindset = 'stressed'
        elif session.avg_response_time > 40:
            session.detected_mindset = 'disengaged'
        else:
            session.detected_mindset = 'neutral'
        
        session.is_active = False
        session.completed_at = timezone.now()
        session.save()
        
        # Update Mastery Vectors automatically
        try:
            from users.mastery_views import calculate_mastery_update
            calculate_mastery_update(session.user, session)
        except Exception as e:
            print(f"Error updating mastery for session {session.id}: {e}")
        
        # Send real-time completion notification (optional - channels may not be installed)
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            channel_layer = get_channel_layer()
            if channel_layer:
                room_group_name = f'quiz_{session.id}'
                async_to_sync(channel_layer.group_send)(
                    room_group_name,
                    {
                        'type': 'quiz_completed',
                        'session_id': str(session.id),
                        'total_score': session.total_score
                    }
                )
        except ImportError:
            pass  # channels not installed, skip WebSocket updates
        except Exception as e:
            print(f"WebSocket completion notification failed: {e}")
        
        # Send notifications to student and parents
        try:
            from users.notifications import notify_quiz_graded
            notify_quiz_graded(session)
        except Exception as e:
            print(f"Quiz graded notification failed: {e}")
        
        return Response({
            'session': QuizSessionSerializer(session).data,
            'message': 'Quiz completed successfully'
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """Get detailed results for a completed quiz session"""
        session = self.get_object()
        
        # Get all responses for this session
        responses = session.responses.all().select_related('question')
        
        # Calculate statistics
        total_questions = responses.count()
        correct_count = responses.filter(is_correct=True).count()
        accuracy = (correct_count / total_questions * 100) if total_questions > 0 else 0
        
        # Group by difficulty
        difficulty_stats = {}
        for level in range(1, 6):
            level_responses = responses.filter(question__difficulty_level=level)
            level_correct = level_responses.filter(is_correct=True).count()
            level_total = level_responses.count()
            if level_total > 0:
                difficulty_stats[f'level_{level}'] = {
                    'total': level_total,
                    'correct': level_correct,
                    'accuracy': (level_correct / level_total * 100)
                }
        
        return Response({
            'session_id': str(session.id),
            'quiz_title': session.quiz.title,
            'student': session.user.get_full_name(),
            'completed_at': session.completed_at,
            'total_score': session.total_score,
            'behavior_score': session.behavior_score,
            'final_ability': session.student_ability,
            'detected_mindset': session.detected_mindset,
            'statistics': {
                'total_questions': total_questions,
                'correct_answers': correct_count,
                'incorrect_answers': total_questions - correct_count,
                'accuracy': accuracy,
                'avg_response_time': session.avg_response_time,
                'difficulty_stats': difficulty_stats
            },
            'responses': ResponseSerializer(responses, many=True).data
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'], url_path='results')
    def results(self, request, pk=None):
        """Get formatted results for the results page"""
        session = self.get_object()
        
        # Permission check
        # We rely on get_queryset to ensure parents only see their children's sessions
        # But we still check roles for strictness if bypassing standard lookup
        is_owner = session.user == request.user
        is_teacher = request.user.role == 'teacher'
        is_parent = request.user.role == 'parent'
        is_staff = request.user.is_staff
        
        if not (is_owner or is_teacher or is_parent or is_staff):
            return Response(
                {"error": "You do not have permission to view these results"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get all responses
        responses = session.responses.all().select_related('question__topic')
        
        # Calculate topic performance
        topic_performance = {}
        for response in responses:
            if response.question.topic:
                topic_name = response.question.topic.name
                if topic_name not in topic_performance:
                    topic_performance[topic_name] = {'correct': 0, 'total': 0}
                
                topic_performance[topic_name]['total'] += 1
                if response.is_correct:
                    topic_performance[topic_name]['correct'] += 1
        
        # Format topic data
        topic_data = []
        for topic, stats in topic_performance.items():
            score = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
            topic_data.append({
                'topic': topic,
                'score': round(score, 1)
            })
        
        # Get enhanced recommendations
        recommendations = self._generate_enhanced_recommendations(session, topic_performance)
        
        # Calculate grade
        score = session.total_score
        if score >= 90:
            grade = 'A'
        elif score >= 80:
            grade = 'B'
        elif score >= 70:
            grade = 'C'
        elif score >= 60:
            grade = 'D'
        else:
            grade = 'F'
        
        # Format responses for question review
        response_data = []
        for idx, response in enumerate(responses, 1):
            response_data.append({
                'question_number': idx,
                'question_text': response.question.question_text,
                'your_answer': response.text_answer if hasattr(response, 'text_answer') and response.text_answer else response.selected_answer,
                'correct_answer': response.question.correct_answer if response.question.question_type == 'mcq' or response.question.question_type == 'multiple_choice' else None,
                'is_correct': response.is_correct,
                'explanation': response.question.explanation,
                'time_taken': int(response.response_time),
                'teacher_feedback': getattr(response, 'teacher_feedback', '')
            })
        
        # Calculate time taken
        time_taken_minutes = 0
        if session.completed_at and session.started_at:
            time_taken_minutes = round((session.completed_at - session.started_at).total_seconds() / 60, 1)
        
        return Response({
            'student_name': session.user.get_full_name() or session.user.username,
            'student_email': session.user.email,
            'quiz_title': session.quiz.title,
            'date_taken': session.completed_at or session.started_at,
            'attempt_number': session.attempt_number,
            'total_score': round(session.total_score, 1), 
            'grade': grade,
            'accuracy': session.accuracy,
            'correct_answers': session.correct_answers,
            'incorrect_answers': session.incorrect_answers,
            'time_taken_minutes': time_taken_minutes,
            'avg_response_time': round(session.avg_response_time, 1), 
            'topic_performance': topic_data,
            'topics': topic_data, 
            'behavior_score': session.behavior_score or 100,
            'detected_mindset': session.detected_mindset,
            'recommendations': recommendations,
            'tab_switches': session.total_tab_switches,
            'hesitations': session.total_hesitations,
            'overall_conduct': 'Excellent' if session.total_tab_switches == 0 else 'Good' if session.total_tab_switches < 3 else 'Fair',
            'responses': response_data
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'], url_path='download-report')
    def download_report(self, request, pk=None):
        """Download PDF report (alias for export-report for consistency)"""
        return self.export_report(request, pk)
    
    @action(detail=True, methods=['get'], url_path='export-report')
    def export_report(self, request, pk=None):
        """Export quiz results as PDF report"""
        from django.http import HttpResponse
        from .pdf_generator import generate_quiz_report_pdf
        
        session = self.get_object()
        
        # Permission check: user can only export their own reports, or teachers/staff can export any
        if session.user != request.user and not request.user.is_staff and request.user.role != 'teacher':
            return Response(
                {"error": "You can only export your own reports"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get all responses for topic breakdown
        responses = session.responses.all().select_related('question__topic')
        
        # Calculate topic performance
        topic_performance = {}
        for response in responses:
            topic_name = response.question.topic.name
            if topic_name not in topic_performance:
                topic_performance[topic_name] = {'correct': 0, 'total': 0}
            
            topic_performance[topic_name]['total'] += 1
            if response.is_correct:
                topic_performance[topic_name]['correct'] += 1
        
        # Format topic data for chart
        topic_data = []
        for topic, stats in topic_performance.items():
            accuracy = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
            topic_data.append({
                'topic': topic[:15],  # Truncate long names for chart
                'accuracy': round(accuracy, 1)
            })
        
        # Get enhanced recommendations
        recommendations = self._generate_enhanced_recommendations(session, topic_performance)
        
        # Prepare session data for PDF
        session_data = {
            'session_id': str(session.id),
            'student_name': session.user.get_full_name() or session.user.username,
            'student_email': session.user.email,
            'quiz_title': session.quiz.title,
            'completed_at': session.completed_at.strftime('%B %d, %Y at %I:%M %p') if session.completed_at else 'In Progress',
            'attempt_number': session.attempt_number,
            'total_score': round(session.total_score, 1),
            'accuracy': round(session.accuracy, 1),
            'correct_answers': session.correct_answers,
            'incorrect_answers': session.incorrect_answers,
            'time_taken': round((session.completed_at - session.started_at).total_seconds() / 60, 1) if session.completed_at else 0,
            'avg_response_time': round(session.avg_response_time, 1),
            'topic_performance': topic_data,
            'proctoring_enabled': True,  # Assuming proctoring is enabled
            'behavior_score': session.behavior_score or 100,
            'total_tab_switches': session.total_tab_switches,
            'total_hesitations': session.total_hesitations,
            'detected_mindset': session.detected_mindset or 'Not Available',
            'recommendations': recommendations[:3],  # Top 3
        }
        
        # Generate PDF
        try:
            pdf_buffer = generate_quiz_report_pdf(session_data)
            
            # Create HTTP response
            response = HttpResponse(pdf_buffer, content_type='application/pdf')
            filename = f"quiz_report_{session.user.username}_{session.quiz.title[:30]}_{session.id}.pdf"
            return response
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return Response({"error": f"Failed to generate report: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _generate_enhanced_recommendations(self, session, topic_performance):
        """Generate descriptive, supportive, and actionable AI recommendations"""
        recommendations = []
        
        # 1. Mindset-based recommendations
        mindset = getattr(session, 'detected_mindset', 'neutral')
        if mindset == 'anxious':
            recommendations.append(
                "Mindset: We noticed signs of mild anxiety during the quiz. This is perfectly normal! "
                "To help you perform better, try a 5-minute deep breathing exercise before your next session. "
                "Building a calm pre-quiz routine can significantly improve your focus and confidence."
            )
        elif mindset == 'confused' or mindset == 'frustrated':
            recommendations.append(
                "Mindset: We detected some moments of confusion. Don't hesitate to use the 'Hint' feature "
                "or review the learning materials for unclear topics. Breaking down complex problems into "
                "smaller steps can help clarify the core concepts."
            )
        elif mindset == 'disengaged' or mindset == 'bored':
            recommendations.append(
                "Mindset: Your engagement seemed to dip slightly. Try shorter, high-intensity study sessions "
                "or use the 'Gamified' mode to keep things interesting. Taking short 'micro-breaks' every "
                "15 minutes can also help maintain your peak focus."
            )
        elif mindset == 'stressed':
            recommendations.append(
                "Mindset: High stress levels were detected, which can sometimes hinder critical thinking. "
                "Remember that mistakes are merely data points for growth. Try breaking your study material "
                "into smaller, 'bite-sized' chunks to make the learning process feel more manageable."
            )
        elif mindset == 'confident' or mindset == 'focused':
            recommendations.append(
                "Mindset: You displayed great confidence and focus! You're clearly 'in the zone.' "
                "Maintain this momentum by challenging yourself with slightly harder topics in your next "
                "session to continue expanding your boundaries."
            )
        else: # neutral or others
            recommendations.append(
                "Mindset: Your learning session was steady and focused. To unlock even better retention, "
                "we recommend shifting from a passive review to active engagement. Try summarizing the key "
                "points of each topic in your own words or teaching the concept to a peer."
            )
            
        # 2. Time Management / Pacing
        avg_time = session.avg_response_time
        if avg_time < 8:
            recommendations.append(
                "Pacing: Your response speed is highly impressive, but answering too quickly can lead to "
                "oversight of subtle details. In your next quiz, try to pause for 5 seconds after reading "
                "each question to ensure you've considered all possible options before committing."
            )
        elif avg_time > 45:
            recommendations.append(
                "Pacing: You're taking a thoughtful amount of time per question, but building speed is also "
                "important for exam readiness. Try some 'Lightning Round' practice sessions where you focus "
                "on identifying key terms quickly to improve your overall response tempo."
            )
            
        # 3. Topic-specific recommendations
        weak_topics = []
        strong_topics = []
        
        for topic, stats in topic_performance.items():
            score = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
            if score < 70:
                weak_topics.append(topic)
                recommendations.append(
                    f"Focus: Based on your performance in **{topic}**, there is a significant opportunity for growth. "
                    f"Your score of {score:.0f}% suggests that the foundational concepts might need a quick refresh. "
                    f"We recommend revisiting the relevant study modules and focused practice problems to build a stronger base."
                )
            elif score >= 90:
                strong_topics.append(topic)
                
        if strong_topics:
            top_strong = strong_topics[:2]
            topics_str = " and ".join(top_strong)
            recommendations.append(
                f"Challenge: You've shown exceptional mastery in **{topics_str}**. "
                f"To keep your progress moving forward, try the 'Advanced Application' quizzes or "
                f"attempt these topics under a tighter time limit to truly cement your expertise."
            )
            
        # 4. General Strategy (Fallback)
        if not recommendations:
             recommendations.append(
                 "Strategy: Your performance across all categories is remarkably balanced. "
                 "Consistency is your strongest asset. Keep up the regular practice schedule, "
                 "and consider exploring interdisciplinary topics that connect your current subjects."
             )
        
        return recommendations
    
    @action(detail=True, methods=['post'], url_path='hide-from-parent')
    def hide_from_parent(self, request, pk=None):
        """Hide quiz session from parent view"""
        session = self.get_object()
        
        if session.user != request.user:
            return Response(
                {"error": "You can only modify your own sessions"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # removed parent connection
        session.save()
        
        return Response(
            {"message": "Session hidden from parent view"},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'], url_path='unhide-from-parent')
    def unhide_from_parent(self, request, pk=None):
        """Unhide quiz session from parent view"""
        session = self.get_object()
        
        if session.user != request.user:
            return Response(
                {"error": "You can only modify your own sessions"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # removed parent connection
        session.save()
        
        return Response(
            {"message": "Session visible to parents"},
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['post'], url_path='reset-attempts')
    def reset_attempts(self, request):
        """
        Teachers can reset quiz attempts for their students.
        Only works for students in their classrooms.
        
        Payload:
        {
            "student_id": "uuid",
            "quiz_id": "uuid"
        }
        """
        from users.models import Classroom
        
        # Only teachers can reset attempts
        if request.user.role != 'teacher':
            return Response(
                {"error": "Only teachers can reset quiz attempts"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        student_id = request.data.get('student_id')
        quiz_id = request.data.get('quiz_id')
        
        if not student_id or not quiz_id:
            return Response(
                {"error": "Both student_id and quiz_id are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        
        # Check for bulk reset operations
        reset_all_students = student_id == 'all'
        reset_all_quizzes = quiz_id == 'all'
        
        # Case 1: Reset ALL students for a specific quiz
        if reset_all_students and not reset_all_quizzes:
            try:
                quiz = Quiz.objects.get(id=quiz_id)
            except Quiz.DoesNotExist:
                return Response(
                    {"error": "Quiz not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Only quiz creator can reset all students
            if quiz.created_by != request.user:
                return Response(
                    {"error": "Only the quiz creator can reset all students' attempts"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            sessions = QuizSession.objects.filter(quiz=quiz)
            sessions_count = sessions.count()
            
            if sessions_count == 0:
                return Response(
                    {"error": "No attempts found for this quiz"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            sessions.delete()
            
            # Log the reset
            QuizResetLog.objects.create(
                teacher=request.user,
                quiz=quiz,
                reset_type='all_students_one_quiz',
                sessions_deleted=sessions_count
            )
            
            return Response(
                {
                    "message": f"Successfully reset {sessions_count} attempt(s) for all students in quiz '{quiz.title}'",
                    "deleted_count": sessions_count
                },
                status=status.HTTP_200_OK
            )
        
        # Case 2: Reset specific student for ALL quizzes
        elif not reset_all_students and reset_all_quizzes:
            try:
                target_user = User.objects.get(id=student_id)
            except User.DoesNotExist:
                return Response(
                    {"error": "User not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Permission check
            is_own_attempt = target_user.id == request.user.id
            
            if not is_own_attempt:
                if target_user.role == 'student':
                    teacher_classrooms = Classroom.objects.filter(
                        models.Q(teacher=request.user) | models.Q(co_teachers=request.user)
                    )
                    student_in_class = teacher_classrooms.filter(students=target_user).exists()
                    
                    if not student_in_class:
                        return Response(
                            {"error": "You can only reset all quizzes for students in your classrooms or yourself"},
                            status=status.HTTP_403_FORBIDDEN
                        )
                else:
                    return Response(
                        {"error": "You can only reset all your own quiz attempts"},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            sessions = QuizSession.objects.filter(user=target_user)
            sessions_count = sessions.count()
            
            if sessions_count == 0:
                return Response(
                    {"error": "No attempts found for this user"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            sessions.delete()
            
            # Log the reset
            QuizResetLog.objects.create(
                teacher=request.user,
                target_user=target_user,
                reset_type='one_student_all_quizzes',
                sessions_deleted=sessions_count
            )
            
            return Response(
                {
                    "message": f"Successfully reset {sessions_count} attempt(s) for {target_user.email} across all quizzes",
                    "deleted_count": sessions_count
                },
                status=status.HTTP_200_OK
            )
        
        # Case 3: Reset ALL students for ALL of teacher's quizzes
        elif reset_all_students and reset_all_quizzes:
            # Teachers can only reset all for THEIR quizzes and THEIR students
            teacher_quizzes = Quiz.objects.filter(created_by=request.user)
            teacher_classrooms = Classroom.objects.filter(
                models.Q(teacher=request.user) | models.Q(co_teachers=request.user)
            )
            teacher_students = User.objects.filter(
                enrolled_classes__in=teacher_classrooms,
                role='student'
            ).distinct()
            
            # Reset sessions for teacher's quizzes OR teacher's students
            sessions = QuizSession.objects.filter(
                models.Q(quiz__in=teacher_quizzes) | models.Q(user__in=teacher_students)
            )
            sessions_count = sessions.count()
            
            if sessions_count == 0:
                return Response(
                    {"error": "No attempts found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            sessions.delete()
            
            # Log the reset
            QuizResetLog.objects.create(
                teacher=request.user,
                reset_type='all_students_all_quizzes',
                sessions_deleted=sessions_count
            )
            
            return Response(
                {
                    "message": f"Successfully reset {sessions_count} attempt(s) for ALL users and ALL quizzes",
                    "deleted_count": sessions_count
                },
                status=status.HTTP_200_OK
            )
        
        # Case 4: Reset specific student + specific quiz (original behavior)
        try:
            # Allow resetting for any user (student or teacher)
            target_user = User.objects.get(id=student_id)
            quiz = Quiz.objects.get(id=quiz_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Quiz.DoesNotExist:
            return Response(
                {"error": "Quiz not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Permission check: Teachers can reset:
        # 1. Their own attempts (for testing)
        # 2. Students in their classrooms
        # 3. Other teachers' attempts if they created the quiz
        
        is_own_attempt = target_user.id == request.user.id
        is_quiz_creator = quiz.created_by == request.user
        
        if not is_own_attempt and not is_quiz_creator:
            # Check if target is a student in teacher's classroom
            if target_user.role == 'student':
                teacher_classrooms = Classroom.objects.filter(
                    models.Q(teacher=request.user) | models.Q(co_teachers=request.user)
                )
                student_in_class = teacher_classrooms.filter(students=target_user).exists()
                
                if not student_in_class:
                    return Response(
                        {"error": "You can only reset attempts for students in your classrooms or your own attempts"},
                        status=status.HTTP_403_FORBIDDEN
                    )
            else:
                return Response(
                    {"error": "You can only reset your own attempts or students in your classrooms"},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Get all sessions for this user and quiz
        sessions = QuizSession.objects.filter(
            user=target_user,
            quiz=quiz
        )
        
        if not sessions.exists():
            return Response(
                {"error": "No attempts found for this user and quiz"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Mark all sessions as reset (soft delete)
        sessions_count = sessions.count()
        sessions.delete()  # Actually delete them to allow fresh attempts
        
        # Log the reset
        QuizResetLog.objects.create(
            teacher=request.user,
            target_user=target_user,
            quiz=quiz,
            reset_type='specific',
            sessions_deleted=sessions_count
        )
        
        # Log the reset action
        from django.utils import timezone
        from users.models import Notification
        
        # Notify the user
        Notification.objects.create(
            user=target_user,
            title="Quiz Attempts Reset",
            message=f"Your attempts for '{quiz.title}' have been reset by {request.user.get_full_name()}. You can now retake the quiz.",
            notification_type="quiz_reset",
            related_object_type="quiz",
            related_object_id=str(quiz.id)
        )
        
        return Response({
            "message": f"Successfully reset {sessions_count} attempt(s) for {student.get_full_name()}",
            "student": student.get_full_name(),
            "quiz": quiz.title,
            "attempts_reset": sessions_count
        }, status=status.HTTP_200_OK)


