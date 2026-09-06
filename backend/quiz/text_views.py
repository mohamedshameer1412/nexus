"""
API Views for Text-Based Questions
Handles submission, AI grading, and teacher review
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response as APIResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q

from quiz.models import QuizSession, Question, Response
from quiz.text_grader import TextAnswerGrader


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_text_answer(request, session_id):
    """
    Submit a text answer for AI grading
    
    POST /api/quiz/sessions/{session_id}/submit-text-answer/
    
    Request Body:
    {
        "question_id": "uuid",
        "text_answer": "Student's written answer...",
        "response_time": 120,
        "hesitation_count": 2,
        "tab_switches": 0
    }
    
    Response:
    {
        "status": "success",
        "response_id": "uuid",
        "ai_grading": {
            "score": 8.5,
            "max_score": 10,
            "feedback": "...",
            "keyword_matches": {...},
            "similarity_score": 0.85
        },
        "grading_status": "ai_graded",
        "requires_teacher_review": true
    }
    """
    try:
        # Get session and validate
        session = get_object_or_404(QuizSession, id=session_id, user=request.user)
        
        if not session.is_active:
            return APIResponse(
                {"error": "Quiz session is not active"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get question
        question_id = request.data.get('question_id')
        question = get_object_or_404(Question, id=question_id)
        
        # Validate question type
        if question.question_type not in ['short_answer', 'essay']:
            return APIResponse(
                {"error": "This endpoint is only for text-based questions"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get text answer
        text_answer = request.data.get('text_answer', '').strip()
        
        if not text_answer:
            return APIResponse(
                {"error": "Text answer cannot be empty"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Count words
        word_count = len(text_answer.split())
        
        # Validate word count
        if question.min_words and word_count < question.min_words:
            return APIResponse(
                {"error": f"Answer must be at least {question.min_words} words. Current: {word_count}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if question.max_words and word_count > question.max_words:
            return APIResponse(
                {"error": f"Answer must not exceed {question.max_words} words. Current: {word_count}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create response object
        response_obj = Response.objects.create(
            session=session,
            question=question,
            text_answer=text_answer,
            word_count=word_count,
            response_time=request.data.get('response_time', 0),
            hesitation_count=request.data.get('hesitation_count', 0),
            tab_switches=request.data.get('tab_switches', 0),
            question_difficulty_at_time=question.difficulty_level,
            grading_status='pending'
        )
        
        # AI Grading (if enabled)
        ai_grading_result = None
        if question.auto_grade:
            try:
                grader = TextAnswerGrader()
                ai_grading_result = grader.grade_answer(
                    student_answer=text_answer,
                    model_answer=question.model_answer,
                    question_text=question.question_text,
                    required_keywords=question.required_keywords,
                    max_score=10.0
                )
                
                # Update response with AI grading
                response_obj.ai_score = ai_grading_result["ai_score"]
                response_obj.ai_feedback = ai_grading_result["ai_feedback"]
                response_obj.similarity_score = ai_grading_result["similarity_score"]
                response_obj.keyword_matches = ai_grading_result["keyword_matches"]
                response_obj.grading_status = 'ai_graded'
                
                # Set final score to AI score initially
                response_obj.final_score = ai_grading_result["ai_score"]
                
                response_obj.save()
                
            except Exception as e:
                # If AI grading fails, mark as pending manual review
                response_obj.grading_status = 'pending'
                response_obj.ai_feedback = f"AI grading failed: {str(e)}"
                response_obj.save()
        
        # Update session stats
        session.current_question_index += 1
        session.save()
        
        return APIResponse({
            "status": "success",
            "response_id": str(response_obj.id),
            "ai_grading": ai_grading_result if ai_grading_result else None,
            "grading_status": response_obj.grading_status,
            "requires_teacher_review": ai_grading_result["requires_teacher_review"] if ai_grading_result else True,
            "word_count": word_count
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return APIResponse(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_pending_reviews(request, session_id=None):
    """
    Get all text answers awaiting teacher review
    
    GET /api/quiz/pending-reviews/
    GET /api/quiz/sessions/{session_id}/pending-reviews/
    
    Query Params:
    - classroom_id: Filter by classroom
    - quiz_id: Filter by quiz
    - status: Filter by grading_status (default: ai_graded)
    
    Response:
    {
        "total_count": 15,
        "pending_reviews": [
            {
                "response_id": "uuid",
                "student_name": "John Doe",
                "question_text": "...",
                "student_answer": "...",
                "word_count": 150,
                "ai_score": 8.5,
                "ai_feedback": "...",
                "keyword_matches": {...},
                "submitted_at": "2026-01-20T10:30:00Z"
            }
        ]
    }
    """
    try:
        # Base query
        if session_id:
            session = get_object_or_404(QuizSession, id=session_id)
            responses = Response.objects.filter(session=session)
        else:
            responses = Response.objects.all()
        
        # Filter by grading status
        grading_status = request.query_params.get('status', 'ai_graded')
        responses = responses.filter(grading_status=grading_status)
        
        # Filter by text-based questions only
        responses = responses.filter(
            Q(question__question_type='short_answer') | Q(question__question_type='essay')
        )
        
        # Additional filters
        classroom_id = request.query_params.get('classroom_id')
        quiz_id = request.query_params.get('quiz_id')
        
        if classroom_id:
            responses = responses.filter(session__quiz__classroom_assignments__classroom_id=classroom_id)
        
        if quiz_id:
            responses = responses.filter(session__quiz_id=quiz_id)
        
        # Order by submission time
        responses = responses.select_related('session__user', 'question').order_by('-timestamp')
        
        # Build response data
        pending_reviews = []
        for resp in responses:
            pending_reviews.append({
                "response_id": str(resp.id),
                "student_name": resp.session.user.get_full_name() or resp.session.user.username,
                "student_id": str(resp.session.user.id),
                "quiz_title": resp.session.quiz.title,
                "question_text": resp.question.question_text,
                "question_type": resp.question.question_type,
                "student_answer": resp.text_answer,
                "word_count": resp.word_count,
                "ai_score": resp.ai_score,
                "ai_feedback": resp.ai_feedback,
                "keyword_matches": resp.keyword_matches,
                "similarity_score": resp.similarity_score,
                "submitted_at": resp.timestamp.isoformat()
            })
        
        return APIResponse({
            "total_count": len(pending_reviews),
            "pending_reviews": pending_reviews
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return APIResponse(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def teacher_review_response(request, response_id):
    """
    Teacher reviews and grades a text answer
    
    POST /api/quiz/responses/{response_id}/teacher-review/
    
    Request Body:
    {
        "teacher_score": 9.0,
        "teacher_feedback": "Excellent work! Consider mentioning...",
        "finalize": true
    }
    
    Response:
    {
        "status": "success",
        "response_id": "uuid",
        "final_score": 9.0,
        "grading_status": "finalized"
    }
    """
    try:
        # Get response
        response_obj = get_object_or_404(Response, id=response_id)
        
        # Validate it's a text-based question
        if response_obj.question.question_type not in ['short_answer', 'essay']:
            return APIResponse(
                {"error": "This endpoint is only for text-based questions"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get teacher scores and feedback
        teacher_score = request.data.get('teacher_score')
        teacher_feedback = request.data.get('teacher_feedback', '')
        finalize = request.data.get('finalize', False)
        
        if teacher_score is None:
            return APIResponse(
                {"error": "teacher_score is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate score
        teacher_score = float(teacher_score)
        if teacher_score < 0 or teacher_score > 10:
            return APIResponse(
                {"error": "Score must be between 0 and 10"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update response
        response_obj.teacher_score = teacher_score
        response_obj.teacher_feedback = teacher_feedback
        response_obj.reviewed_by = request.user
        response_obj.reviewed_at = timezone.now()
        
        if finalize:
            # Finalize with teacher score
            response_obj.final_score = teacher_score
            response_obj.grading_status = 'finalized'
            response_obj.is_correct = teacher_score >= 6.0  # 60% passing
        else:
            # Just mark as reviewed, not finalized
            response_obj.grading_status = 'teacher_reviewed'
        
        response_obj.save()
        
        return APIResponse({
            "status": "success",
            "response_id": str(response_obj.id),
            "final_score": response_obj.final_score,
            "grading_status": response_obj.grading_status,
            "reviewed_at": response_obj.reviewed_at.isoformat()
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return APIResponse(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
