"""
PDF Question Import API View
Handles PDF upload and question extraction using Gemini AI
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from django.conf import settings
from django.core.cache import cache
import uuid
import threading
import io
from .pdf_parser import parse_pdf_questions
from .models import Question, Topic, Subtopic
from .serializers import QuestionSerializer
import logging

logger = logging.getLogger(__name__)


class PDFQuestionImportView(APIView):
    """
    API endpoint for importing questions from PDF files
    
    POST /api/quiz/import-pdf/
    - Upload PDF file
    - Extract text and parse questions using Gemini AI
    - Return parsed questions for review
    
    POST /api/quiz/import-pdf/confirm/
    - Confirm and save questions to database
    """
    
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def _process_pdf_task(self, task_id, pdf_bytes, use_ai):
        try:
            # Create a BytesIO object from the bytes
            pdf_file_obj = io.BytesIO(pdf_bytes)
            
            # Parse PDF (GEMINI API CALL HAPPENS HERE if use_ai=True)
            result = parse_pdf_questions(pdf_file_obj, use_ai=use_ai)
            
            if result.get('requires_manual_review'):
                cache.set(f"pdf_task_{task_id}", {
                    "status": "partial_success",
                    "message": "PDF text extracted, but AI parsing failed. Please review manually.",
                    "extracted_text": result.get('extracted_text', ''),
                    "error": result.get('error', ''),
                    "questions": []
                }, timeout=3600)
            else:
                cache.set(f"pdf_task_{task_id}", {
                    "status": "success",
                    "message": f"Successfully parsed {result['total_questions']} questions",
                    "questions": result['questions'],
                    "total_questions": result['total_questions'],
                    "extracted_text_preview": result.get('extracted_text', '')[:500]
                }, timeout=3600)
                
        except Exception as e:
            logger.error(f"PDF import task error: {str(e)}")
            cache.set(f"pdf_task_{task_id}", {
                "status": "error",
                "message": str(e)
            }, timeout=3600)

    def post(self, request, *args, **kwargs):
        """
        Handle PDF upload and parsing
        
        Expected data:
        - pdf_file: PDF file upload
        - use_ai: boolean (optional, default True)
        """
        # Permission check: Only teachers can import questions
        if request.user.role != 'teacher' and not request.user.is_staff:
            return Response(
                {"error": "Only teachers can import questions"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if Gemini API key is configured
        if not settings.GEMINI_API_KEY:
            return Response(
                {
                    "error": "Gemini API key not configured",
                    "message": "Please add GEMINI_API_KEY to your .env file to use AI-powered question import"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get uploaded file
        pdf_file = request.FILES.get('pdf_file')
        if not pdf_file:
            return Response(
                {"error": "No PDF file provided"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file type
        if not pdf_file.name.endswith('.pdf'):
            return Response(
                {"error": "File must be a PDF"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file size (max 10MB)
        if pdf_file.size > 10 * 1024 * 1024:
            return Response(
                {"error": "File size must be less than 10MB"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get use_ai parameter (default True)
        use_ai = request.data.get('use_ai', 'true').lower() == 'true'
        
        # Read file contents into bytes before starting the thread
        # This prevents the file from being closed/deleted when the view returns
        pdf_bytes = pdf_file.read()
        
        # Generate task ID and save initial state
        task_id = str(uuid.uuid4())
        cache.set(f"pdf_task_{task_id}", {"status": "processing"}, timeout=3600)
        
        # Start background thread
        thread = threading.Thread(target=self._process_pdf_task, args=(task_id, pdf_bytes, use_ai))
        thread.daemon = True
        thread.start()
        
        return Response({
            "task_id": task_id,
            "status": "processing",
            "message": "PDF upload successful. AI parsing started in background."
        }, status=status.HTTP_202_ACCEPTED)

class PDFQuestionImportStatusView(APIView):
    """
    Check status of an asynchronous PDF import task
    
    GET /api/quiz/import-pdf/status/?task_id=...
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        task_id = request.query_params.get('task_id')
        
        if not task_id:
            return Response({"error": "Task ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        task_data = cache.get(f"pdf_task_{task_id}")
        
        if not task_data:
            return Response({"error": "Task not found or expired"}, status=status.HTTP_404_NOT_FOUND)
            
        return Response(task_data, status=status.HTTP_200_OK)


class PDFQuestionConfirmView(APIView):
    """
    Confirm and save parsed questions to database
    
    POST /api/quiz/import-pdf/confirm/
    Expected data:
    - questions: Array of question objects
    - topic_id: UUID of topic to assign questions to
    - subtopic_id: UUID of subtopic (optional)
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        """Save confirmed questions to database"""
        
        # Permission check
        if request.user.role != 'teacher' and not request.user.is_staff:
            return Response(
                {"error": "Only teachers can import questions"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        questions_data = request.data.get('questions', [])
        topic_id = request.data.get('topic_id')
        subtopic_id = request.data.get('subtopic_id')
        
        if not questions_data:
            return Response(
                {"error": "No questions provided"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not topic_id:
            return Response(
                {"error": "Topic ID is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate topic exists
        try:
            topic = Topic.objects.get(id=topic_id)
        except Topic.DoesNotExist:
            return Response(
                {"error": "Topic not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Validate subtopic if provided
        subtopic = None
        if subtopic_id:
            try:
                subtopic = Subtopic.objects.get(id=subtopic_id, topic=topic)
            except Subtopic.DoesNotExist:
                return Response(
                    {"error": "Subtopic not found or does not belong to the specified topic"},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Create questions
        created_questions = []
        errors = []
        
        for idx, q_data in enumerate(questions_data):
            try:
                # Prepare question data
                q_type = q_data.get('question_type', 'mcq').lower()
                
                common_data = {
                    'topic': topic,
                    'subtopic': subtopic,
                    'question_text': q_data.get('question_text', ''),
                    'question_type': q_type,
                    'difficulty_level': q_data.get('difficulty_level', 3),
                    'explanation': q_data.get('explanation', ''),
                    'created_by': request.user
                }

                if q_type == 'mcq':
                    question = Question.objects.create(
                        **common_data,
                        option_a=q_data.get('option_a', ''),
                        option_b=q_data.get('option_b', ''),
                        option_c=q_data.get('option_c', ''),
                        option_d=q_data.get('option_d', ''),
                        correct_answer=q_data.get('correct_answer', 'A')
                    )
                else:
                    # Short answer / Essay
                    question = Question.objects.create(
                        **common_data,
                        model_answer=q_data.get('model_answer', ''),
                        required_keywords=q_data.get('required_keywords', []),
                        auto_grade=q_data.get('auto_grade', True)
                    )
                created_questions.append(QuestionSerializer(question).data)
            except Exception as e:
                errors.append({
                    "question_index": idx,
                    "error": str(e)
                })
        
        return Response({
            "status": "success",
            "message": f"Successfully created {len(created_questions)} questions",
            "created_questions": len(created_questions),
            "errors": errors,
            "questions": created_questions
        }, status=status.HTTP_201_CREATED)
