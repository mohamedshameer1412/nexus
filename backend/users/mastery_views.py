"""
Mastery Tracking Integration Views
Updates mastery vectors after quiz completion and provides mastery dashboard
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Avg, Count, Q

from users.models import MasteryVector
from users.serializers import MasteryVectorSerializer, MasteryDashboardSerializer
from quiz.models import QuizSession, Response as QuizResponse


def calculate_mastery_update(user, session):
    """
    Core logic to update mastery vectors for a session.
    Returns list of updates.
    """
    # Get all responses for this session
    responses = QuizResponse.objects.filter(session=session).select_related('question', 'question__topic', 'question__subtopic')
    
    if not responses.exists():
        return []
    
    mastery_updates = []
    
    # Group responses by concept (using topic/subtopic as concept_id)
    concept_responses = {}
    for response in responses:
        # Use subtopic as concept if available, otherwise use topic
        concept_id = f"{response.question.topic.name}"
        if response.question.subtopic:
            concept_id = f"{response.question.topic.name}_{response.question.subtopic.name}"
        
        if concept_id not in concept_responses:
            concept_responses[concept_id] = []
        concept_responses[concept_id].append(response)
    
    # Update mastery for each concept
    for concept_id, concept_resps in concept_responses.items():
        # Get or create mastery vector
        mastery, created = MasteryVector.objects.get_or_create(
            user=user,
            concept_id=concept_id,
            defaults={
                'mastery_score': 0.0,
                'initial_score': 0.0
            }
        )
        
        previous_mastery = mastery.mastery_score
        
        # Update for each response
        for resp in concept_resps:
            mastery.update_mastery(
                is_correct=resp.is_correct,
                time_spent=int(resp.response_time)
            )
        
        mastery_updates.append({
            'concept_id': concept_id,
            'previous_mastery': round(previous_mastery, 3),
            'new_mastery': round(mastery.mastery_score, 3),
            'attempts_count': mastery.attempts_count,
            'correct_count': mastery.correct_count,
            'accuracy': round((mastery.correct_count / mastery.attempts_count) * 100, 2) if mastery.attempts_count > 0 else 0
        })
    
    return mastery_updates


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_mastery_after_quiz(request, session_id):
    """
    Update mastery vectors after quiz completion
    
    POST /api/quiz/sessions/{session_id}/update-mastery/
    """
    try:
        session = QuizSession.objects.get(id=session_id, user=request.user)
        
        if session.is_active:
            return Response({
                'status': 'error',
                'message': 'Quiz session is still active. Complete the quiz first.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        mastery_updates = calculate_mastery_update(request.user, session)
        
        if not mastery_updates:
             return Response({
                'status': 'error',
                'message': 'No responses found or no updates made'
            }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'status': 'success',
            'mastery_updates': mastery_updates,
            'total_concepts_updated': len(mastery_updates)
        }, status=status.HTTP_200_OK)
    
    except QuizSession.DoesNotExist:
        return Response({
            'status': 'error',
            'message': 'Quiz session not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_mastery_dashboard(request):
    """
    Get student's mastery dashboard with weak/strong concepts
    
    GET /api/users/mastery-dashboard/
    """
    try:
        user = request.user
        target_user = user

        # Get all mastery vectors for user
        mastery_vectors = MasteryVector.objects.filter(user=target_user)
        
        if not mastery_vectors.exists():
            return Response({
                'status': 'success',
                'overall_mastery': 0.0,
                'total_concepts': 0,
                'mastered_concepts': 0,
                'weak_concepts': [],
                'strong_concepts': [],
                'mastery_by_subject': {}
            }, status=status.HTTP_200_OK)
        
        # Calculate overall mastery
        overall_mastery = mastery_vectors.aggregate(Avg('mastery_score'))['mastery_score__avg']
        
        # Count mastered concepts (mastery >= 0.7)
        mastered_count = mastery_vectors.filter(mastery_score__gte=0.7).count()
        
        # Get weak concepts (mastery < 0.5, sorted by lowest)
        weak_concepts = mastery_vectors.filter(mastery_score__lt=0.5).order_by('mastery_score')[:5]
        
        # Get strong concepts (mastery >= 0.8, sorted by highest)
        strong_concepts = mastery_vectors.filter(mastery_score__gte=0.8).order_by('-mastery_score')[:5]
        
        # Calculate mastery by subject (extract from concept_id)
        mastery_by_subject = {}
        for mv in mastery_vectors:
            # Extract subject from concept_id (format: "Subject_Subtopic" or "Subject")
            subject = mv.concept_id.split('_')[0]
            if subject not in mastery_by_subject:
                mastery_by_subject[subject] = []
            mastery_by_subject[subject].append(mv.mastery_score)
        
        # Average mastery per subject
        mastery_by_subject = {
            subject: round(sum(scores) / len(scores), 3)
            for subject, scores in mastery_by_subject.items()
        }
        
        return Response({
            'status': 'success',
            'overall_mastery': round(overall_mastery, 3),
            'total_concepts': mastery_vectors.count(),
            'mastered_concepts': mastered_count,
            'weak_concepts': MasteryVectorSerializer(weak_concepts, many=True).data,
            'strong_concepts': MasteryVectorSerializer(strong_concepts, many=True).data,
            'mastery_by_subject': mastery_by_subject
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_concept_mastery(request, concept_id):
    """
    Get detailed mastery data for a specific concept
    
    GET /api/users/mastery/{concept_id}/
    """
    try:
        mastery = MasteryVector.objects.get(user=request.user, concept_id=concept_id)
        serializer = MasteryVectorSerializer(mastery)
        
        return Response({
            'status': 'success',
            'mastery': serializer.data
        }, status=status.HTTP_200_OK)
    
    except MasteryVector.DoesNotExist:
        return Response({
            'status': 'error',
            'message': 'Mastery data not found for this concept'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
