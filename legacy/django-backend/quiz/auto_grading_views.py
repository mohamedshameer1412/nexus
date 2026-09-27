
"""
Auto-Grading API Views
Provides endpoints for AI-powered grading of text-based responses
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response as DRFResponse
from django.shortcuts import get_object_or_404

from quiz.models import Response as QuizResponse, Question
from utils.gemini_service import get_gemini_service


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def auto_grade_response(request, response_id):
    """
    Auto-grade a single text-based response using Gemini AI.
    
    POST /api/responses/{response_id}/auto-grade/
    
    Returns:
        {
            "score": 85,
            "feedback": "Good explanation...",
            "keywords_found": ["keyword1", "keyword2"],
            "is_correct": true,
            "grading_status": "graded"
        }
    """
    response_obj = get_object_or_404(QuizResponse, id=response_id)
    question = response_obj.question
    
    # Validate question type
    if question.question_type not in ['short_answer', 'essay']:
        return DRFResponse(
            {'error': 'Auto-grading only available for text-based questions'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if auto-grading is enabled
    if not question.auto_grade:
        return DRFResponse(
            {'error': 'Auto-grading is disabled for this question'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check permissions (teacher or student who submitted)
    if request.user.role != 'teacher' and response_obj.user != request.user:
        return DRFResponse(
            {'error': 'You do not have permission to grade this response'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        # Use Gemini service
        gemini = get_gemini_service()
        result = gemini.grade_text_answer(
            question_text=question.question_text,
            student_answer=response_obj.text_answer or '',
            model_answer=question.model_answer or '',
            required_keywords=question.required_keywords or [],
            max_score=100
        )
        
        # Update response
        response_obj.ai_score = result['score']
        response_obj.ai_feedback = result['feedback']
        response_obj.is_correct = result['is_correct']
        response_obj.grading_status = 'graded'
        response_obj.save()
        
        return DRFResponse({
            'score': result['score'],
            'feedback': result['feedback'],
            'keywords_found': result['keywords_found'],
            'is_correct': result['is_correct'],
            'grading_status': 'graded'
        })
        
    except Exception as e:
        return DRFResponse(
            {'error': f'Grading failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_model_answer(request):
    """
    Generate a model answer for a question using Gemini AI.
    
    POST /api/questions/generate-model-answer/
    Body: {
        "question_text": "What is machine learning?",
        "question_type": "short_answer",
        "topic": "Machine Learning",
        "min_words": 50,
        "max_words": 200
    }
    
    Returns:
        {
            "model_answer": "Machine learning is...",
            "keywords": ["ml", "data", "algorithms"]
        }
    """
    # Only teachers can generate model answers
    if request.user.role != 'teacher':
        return DRFResponse(
            {'error': 'Only teachers can generate model answers'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    question_text = request.data.get('question_text')
    question_type = request.data.get('question_type', 'short_answer')
    topic = request.data.get('topic', 'General')
    min_words = request.data.get('min_words', 50)
    max_words = request.data.get('max_words', 200)
    
    if not question_text:
        return DRFResponse(
            {'error': 'question_text is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        gemini = get_gemini_service()
        
        # Generate model answer
        model_answer = gemini.generate_model_answer(
            question_text=question_text,
            question_type=question_type,
            topic=topic,
            min_words=min_words,
            max_words=max_words
        )
        
        # Extract keywords
        keywords = gemini.extract_keywords(
            question_text=question_text,
            model_answer=model_answer,
            count=5
        )
        
        return DRFResponse({
            'model_answer': model_answer,
            'keywords': keywords
        })
        
    except Exception as e:
        return DRFResponse(
            {'error': f'Generation failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def batch_auto_grade(request):
    """
    Auto-grade multiple responses at once.
    
    POST /api/responses/batch-auto-grade/
    Body: {
        "response_ids": ["uuid1", "uuid2", "uuid3"],
        "question_id": "optional-uuid"  // Grade all responses for this question
    }
    
    Returns:
        {
            "graded": 10,
            "failed": 2,
            "results": [...]
        }
    """
    # Only teachers can batch grade
    if request.user.role != 'teacher':
        return DRFResponse(
            {'error': 'Only teachers can batch grade responses'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    response_ids = request.data.get('response_ids', [])
    question_id = request.data.get('question_id')
    
    # Build query
    if question_id:
        responses = QuizResponse.objects.filter(
            question_id=question_id,
            question__question_type__in=['short_answer', 'essay'],
            question__auto_grade=True,
            grading_status='pending'
        )
    elif response_ids:
        responses = QuizResponse.objects.filter(
            id__in=response_ids,
            question__question_type__in=['short_answer', 'essay'],
            question__auto_grade=True
        )
    else:
        return DRFResponse(
            {'error': 'Provide either response_ids or question_id'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    gemini = get_gemini_service()
    graded_count = 0
    failed_count = 0
    results = []
    
    for response_obj in responses[:50]:  # Limit to 50 at a time
        try:
            question = response_obj.question
            
            result = gemini.grade_text_answer(
                question_text=question.question_text,
                student_answer=response_obj.text_answer or '',
                model_answer=question.model_answer or '',
                required_keywords=question.required_keywords or [],
                max_score=100
            )
            
            # Update response
            response_obj.ai_score = result['score']
            response_obj.ai_feedback = result['feedback']
            response_obj.is_correct = result['is_correct']
            response_obj.grading_status = 'graded'
            response_obj.save()
            
            graded_count += 1
            results.append({
                'response_id': str(response_obj.id),
                'score': result['score'],
                'status': 'success'
            })
            
        except Exception as e:
            failed_count += 1
            results.append({
                'response_id': str(response_obj.id),
                'error': str(e),
                'status': 'failed'
            })
    
    return DRFResponse({
        'graded': graded_count,
        'failed': failed_count,
        'total': graded_count + failed_count,
        'results': results
    })
