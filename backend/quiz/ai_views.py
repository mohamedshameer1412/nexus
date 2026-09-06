"""
API Views for AI Quiz Generation
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from quiz.models import Topic, Question, AIGeneratedQuestion
from quiz.ai_generator import QuizGenerator


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_questions(request):
    """
    Generate quiz questions using AI
    
    POST /api/quiz/generate-questions/
    Body: {
        "topic_id": "uuid",
        "num_questions": 10,
        "difficulty": "medium",  // "easy", "medium", "hard"
        "question_type": "mcq",  // "mcq", "true_false", "fill_blank"
        "model": "gpt-4o"  // optional, defaults to "gpt-4o"
    }
    """
    # Only teachers can generate questions
    if request.user.role != 'teacher' and not request.user.is_staff:
        return Response({
            'error': 'Only teachers can generate questions'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Validate required fields
    topic_id = request.data.get('topic_id')
    num_questions = request.data.get('num_questions', 10)
    difficulty = request.data.get('difficulty', 'medium')
    question_type = request.data.get('question_type', 'mcq')
    model = request.data.get('model', 'gpt-4o')
    
    if not topic_id:
        return Response({
            'error': 'topic_id is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Validate num_questions
    try:
        num_questions = int(num_questions)
        if num_questions < 1 or num_questions > 50:
            return Response({
                'error': 'num_questions must be between 1 and 50'
            }, status=status.HTTP_400_BAD_REQUEST)
    except (ValueError, TypeError):
        return Response({
            'error': 'num_questions must be a valid integer'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Validate difficulty
    if difficulty not in ['easy', 'medium', 'hard']:
        return Response({
            'error': 'difficulty must be "easy", "medium", or "hard"'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Validate question_type
    if question_type not in ['mcq', 'true_false', 'fill_blank']:
        return Response({
            'error': 'question_type must be "mcq", "true_false", or "fill_blank"'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Get topic
    topic = get_object_or_404(Topic, id=topic_id)
    
    try:
        # Initialize generator
        generator = QuizGenerator(model=model)
        
        # Generate questions
        result = generator.generate_questions(
            topic=topic,
            num_questions=num_questions,
            difficulty=difficulty,
            question_type=question_type,
            user=request.user
        )
        
        return Response(result, status=status.HTTP_200_OK)
        
    except ValueError as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'error': f'Failed to generate questions: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_generated_questions(request):
    """
    Save AI-generated questions to database
    
    POST /api/quiz/save-generated-questions/
    Body: {
        "topic_id": "uuid",
        "questions": [...],  // Array of question objects from generate_questions
        "metadata": {...},   // Metadata from generate_questions
        "prompt": "..."      // Prompt from generate_questions
    }
    """
    # Only teachers can save questions
    if request.user.role != 'teacher' and not request.user.is_staff:
        return Response({
            'error': 'Only teachers can save questions'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Validate required fields
    topic_id = request.data.get('topic_id')
    questions_data = request.data.get('questions', [])
    metadata = request.data.get('metadata', {})
    prompt = request.data.get('prompt', '')
    
    if not topic_id:
        return Response({
            'error': 'topic_id is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if not questions_data:
        return Response({
            'error': 'questions array is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Get topic
    topic = get_object_or_404(Topic, id=topic_id)
    
    try:
        # Get model from metadata
        model = metadata.get('model', 'gpt-4o')
        generator = QuizGenerator(model=model)
        
        # Save questions
        created_questions = generator.save_generated_questions(
            questions_data=questions_data,
            topic=topic,
            metadata=metadata,
            prompt=prompt,
            user=request.user
        )
        
        return Response({
            'status': 'success',
            'message': f'Successfully saved {len(created_questions)} questions',
            'question_ids': [str(q.id) for q in created_questions]
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'error': f'Failed to save questions: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_ai_generated_questions(request):
    """
    Get all AI-generated questions for the current user
    
    GET /api/quiz/ai-generated-questions/
    Query params:
        - approved: true/false (optional)
        - topic_id: uuid (optional)
    """
    # Only teachers can view their AI-generated questions
    if request.user.role != 'teacher' and not request.user.is_staff:
        return Response({
            'error': 'Only teachers can view AI-generated questions'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Get query params
    approved = request.query_params.get('approved')
    topic_id = request.query_params.get('topic_id')
    
    # Build queryset
    queryset = AIGeneratedQuestion.objects.filter(generated_by=request.user)
    
    if approved is not None:
        is_approved = approved.lower() == 'true'
        queryset = queryset.filter(is_approved=is_approved)
    
    if topic_id:
        queryset = queryset.filter(question__topic_id=topic_id)
    
    # Serialize data
    data = []
    for ai_question in queryset.select_related('question', 'question__topic'):
        data.append({
            'id': str(ai_question.id),
            'question_id': str(ai_question.question.id),
            'question_text': ai_question.question.question_text,
            'topic': ai_question.question.topic.name,
            'difficulty': ai_question.question.get_difficulty_level_display(),
            'model_used': ai_question.model_used,
            'is_approved': ai_question.is_approved,
            'created_at': ai_question.created_at,
            'generation_metadata': ai_question.generation_metadata
        })
    
    return Response(data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_ai_question(request, question_id):
    """
    Approve an AI-generated question
    
    POST /api/quiz/ai-generated-questions/{question_id}/approve/
    """
    # Only teachers can approve questions
    if request.user.role != 'teacher' and not request.user.is_staff:
        return Response({
            'error': 'Only teachers can approve questions'
        }, status=status.HTTP_403_FORBIDDEN)
    
    ai_question = get_object_or_404(AIGeneratedQuestion, id=question_id)
    
    # Check ownership
    if ai_question.generated_by != request.user and not request.user.is_staff:
        return Response({
            'error': 'You can only approve your own generated questions'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Approve question
    from django.utils import timezone
    ai_question.is_approved = True
    ai_question.reviewed_by = request.user
    ai_question.reviewed_at = timezone.now()
    ai_question.save()
    
    return Response({
        'status': 'success',
        'message': 'Question approved successfully'
    }, status=status.HTTP_200_OK)
