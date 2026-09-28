"""
Learning DNA Onboarding Views
Handles student onboarding, diagnostic testing, and learning profile creation
"""
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
import numpy as np

from users.models import LearningProfile, SubjectConfidence, MasteryVector, User, Notification, Achievement
from users.serializers import (
    LearningProfileSerializer, 
    LearningProfileCreateSerializer,
    SubjectConfidenceSerializer,
    MasteryVectorSerializer,
    MasteryDashboardSerializer
)
from quiz.models import Quiz, QuizSession, Question, Response as QuizResponse, Topic
import random


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_learning_profile(request):
    """
    Create learning profile for student during onboarding
    
    POST /api/users/learning-profile/create/
    Body: {
        "learning_style": "visual",
        "preferred_study_time": "evening",
        "subject_confidences": [
            {"subject": "mathematics", "confidence_level": 4},
            {"subject": "science", "confidence_level": 3}
        ]
    }
    """
    # Check if user already has a profile
    if hasattr(request.user, 'learning_profile'):
        return Response({
            'status': 'error',
            'message': 'Learning profile already exists for this user'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    serializer = LearningProfileCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            'status': 'error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        with transaction.atomic():
            # Create learning profile
            profile = LearningProfile.objects.create(
                user=request.user,
                learning_style=serializer.validated_data['learning_style'],
                preferred_study_time=serializer.validated_data.get('preferred_study_time')
            )
            
            # Create subject confidences
            for conf_data in serializer.validated_data['subject_confidences']:
                SubjectConfidence.objects.create(
                    profile=profile,
                    subject=conf_data['subject'],
                    confidence_level=conf_data['confidence_level']
                )
            
            return Response({
                'status': 'success',
                'profile_id': str(profile.id),
                'message': 'Learning profile created. Ready for diagnostic test.',
                'next_step': '/api/users/diagnostic-test/start/'
            }, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_diagnostic_test(request):
    """
    Start diagnostic test for initial ability estimation
    
    POST /api/users/diagnostic-test/start/
    Body: {
        "num_questions": 20
    }
    """
    # Check if user has learning profile
    if not hasattr(request.user, 'learning_profile'):
        return Response({
            'status': 'error',
            'message': 'Please create learning profile first'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Diagnostic test can now be taken multiple times to track improvement.
    # The first one still counts for onboarding completion if not already done.
    
    num_questions = request.data.get('num_questions', 20)
    
    if num_questions < 10 or num_questions > 100:
        return Response({
            'status': 'error',
            'message': 'Number of questions must be between 10 and 100'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if enough questions exist
    total_questions = Question.objects.count()
    if total_questions < num_questions:
        return Response({
            'status': 'error',
            'message': f'Insufficient questions in database. Need {num_questions}, have {total_questions}'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Create or get diagnostic quiz session
        # Use filter().first() to avoid MultipleObjectsReturned if duplicates exist
        diagnostic_quiz = Quiz.objects.filter(title="Diagnostic Test").first()
        
        if not diagnostic_quiz:
            diagnostic_quiz = Quiz.objects.create(
                title="Diagnostic Test",
                description='Initial ability estimation test',
                total_questions=num_questions,
                is_adaptive=True,
                created_by=request.user
            )
        
        # Update total_questions if changed (NOTE: This affects the global diagnostic quiz)
        if diagnostic_quiz.total_questions != num_questions:
            diagnostic_quiz.total_questions = num_questions
            diagnostic_quiz.save()
        
        # Calculate attempt number
        previous_attempts = QuizSession.objects.filter(
            user=request.user,
            quiz=diagnostic_quiz
        ).count()
        attempt_number = previous_attempts + 1

        # Create quiz session
        session = QuizSession.objects.create(
            user=request.user,
            quiz=diagnostic_quiz,
            started_at=timezone.now(),
            current_difficulty_level=3,  # Start at medium
            student_ability=0.0,  # Initial theta
            attempt_number=attempt_number
        )
        
        # Select first question (medium difficulty)
        first_question = Question.objects.filter(difficulty_level=3).order_by('?').first()
        
        return Response({
            'status': 'success',
            'session_id': str(session.id),
            'total_questions': num_questions,
            'time_limit': 30,  # 30 minutes
            'first_question': {
                'question_id': str(first_question.id),
                'question_text': first_question.question_text,
                'options': {
                    'A': first_question.option_a,
                    'B': first_question.option_b,
                    'C': first_question.option_c,
                    'D': first_question.option_d
                },
                'question_type': first_question.question_type,
                'difficulty_level': first_question.difficulty_level
            }
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def irt_probability(theta, difficulty, discrimination=1.0, guessing=0.0):
    """Calculate probability of correct answer using 3PL IRT model"""
    return guessing + (1 - guessing) / (1 + np.exp(-discrimination * (theta - difficulty)))


def update_irt_ability(theta, is_correct, difficulty, discrimination=1.0, learning_rate=0.3):
    """Update student ability using gradient ascent"""
    p_correct = irt_probability(theta, difficulty, discrimination)
    gradient = (is_correct - p_correct) * discrimination * p_correct * (1 - p_correct)
    return theta + learning_rate * gradient


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_diagnostic_answer(request):
    """
    Submit answer for diagnostic test question
    
    POST /api/users/diagnostic-test/submit-answer/
    Body: {
        "session_id": "uuid",
        "question_id": "uuid",
        "selected_answer": "B",
        "response_time": 12.5,
        "hesitation_count": 1
    }
    """
    session_id = request.data.get('session_id')
    question_id = request.data.get('question_id')
    selected_answer = request.data.get('selected_answer')
    response_time = request.data.get('response_time', 10.0)
    hesitation_count = request.data.get('hesitation_count', 0)
    
    try:
        session = QuizSession.objects.get(id=session_id, user=request.user, is_active=True)
        question = Question.objects.get(id=question_id)
        
        # Check if question already answered
        existing_response = QuizResponse.objects.filter(session=session, question=question).first()
        is_retry = False
        
        if existing_response:
             is_retry = True
             # If it's a retry, we use existing data essentially
             # We need to set variables that are used later
             is_correct = existing_response.is_correct
             new_theta = session.student_ability # Already updated
        
        if not is_retry:
            # Normal flow - Create response
            is_correct = False
            
            response_data = {
                'session': session,
                'question': question,
                'response_time': response_time,
                'hesitation_count': hesitation_count,
                'question_difficulty_at_time': question.difficulty_level
            }
    
            if question.question_type == 'mcq':
                is_correct = (selected_answer == question.correct_answer)
                response_data['selected_answer'] = selected_answer
                response_data['is_correct'] = is_correct
    
            quiz_response = QuizResponse.objects.create(**response_data)
            
            # Update IRT ability
            current_theta = session.student_ability
            new_theta = update_irt_ability(
                current_theta,
                is_correct,
                question.irt_difficulty,
                question.irt_discrimination
            )
            
            session.student_ability = new_theta
            session.current_question_index += 1
            
            if is_correct:
                session.correct_answers += 1
            else:
                session.incorrect_answers += 1
            
            session.save()
        
        # Select next question based on updated ability
        questions_remaining = session.quiz.total_questions - session.current_question_index
        
        # Prepare feedback data (always return result of current submission)
        feedback_data = {
            'status': 'success',
            'is_correct': is_correct,
            'current_ability': round(new_theta, 3),
            'questions_remaining': questions_remaining,
            'correct_answer': question.correct_answer,
            'explanation': question.explanation,
            'question_type': question.question_type,
        }

        if questions_remaining > 0:
            # Map theta to difficulty level (1-5)
            if new_theta < -1.0:
                target_difficulty = 1
            elif new_theta < -0.5:
                target_difficulty = 2
            elif new_theta < 0.5:
                target_difficulty = 3
            elif new_theta < 1.0:
                target_difficulty = 4
            else:
                target_difficulty = 5
            
            # Get answered question IDs
            answered_ids = QuizResponse.objects.filter(session=session).values_list('question_id', flat=True)
            
            # Select next question
            next_question = Question.objects.filter(
                difficulty_level=target_difficulty
            ).exclude(id__in=answered_ids).order_by('?').first()
            
            if not next_question:
                # Fallback: any unanswered question
                next_question = Question.objects.exclude(id__in=answered_ids).order_by('?').first()
            
            if next_question:
                # Add next question data
                feedback_data['next_question'] = {
                    'question_id': str(next_question.id),
                    'question_text': next_question.question_text,
                    'question_type': next_question.question_type,
                    'options': {
                        'A': next_question.option_a,
                        'B': next_question.option_b,
                        'C': next_question.option_c,
                        'D': next_question.option_d
                    },
                    'difficulty_level': next_question.difficulty_level
                }
            else:
                 # No more questions found (edge case)
                 feedback_data['message'] = 'No more questions available. Diagnostic test complete.'
                 feedback_data['questions_remaining'] = 0

        else:
             feedback_data['message'] = 'Diagnostic test complete. Call /complete/ endpoint.'

        return Response(feedback_data, status=status.HTTP_200_OK)
    
    except QuizSession.DoesNotExist:
        return Response({
            'status': 'error',
            'message': 'Invalid session ID'
        }, status=status.HTTP_404_NOT_FOUND)
    except Question.DoesNotExist:
        return Response({
            'status': 'error',
            'message': 'Invalid question ID'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


from django.utils import timezone
from users.serializers import LearningProfileSerializer
from utils.report_generator import send_diagnostic_report_email
import threading

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_diagnostic_test(request):
    """
    Complete diagnostic test and update learning profile
    
    POST /api/users/diagnostic-test/complete/
    Body: {
        "session_id": "uuid"
    }
    """
    session_id = request.data.get('session_id')
    
    try:
        session = QuizSession.objects.get(id=session_id, user=request.user, is_active=True)
        
        # Check if test is complete
        responses = QuizResponse.objects.filter(session=session)
        if responses.count() < session.quiz.total_questions:
            return Response({
                'status': 'error',
                'message': f'Test incomplete. Answered {responses.count()}/{session.quiz.total_questions} questions'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Calculate final metrics
        final_ability = session.student_ability
        
        # Calculate learning speed (improvement rate)
        theta_values = []
        for i, resp in enumerate(responses.order_by('timestamp')):
            theta_values.append(session.student_ability if i == responses.count()-1 else 0.0)
        
        learning_speed = (final_ability - 0.0) / responses.count() if responses.count() > 0 else 1.0
        learning_speed = max(0.5, min(1.5, 1.0 + learning_speed))  # Normalize to 0.5-1.5
        
        # Calculate guessing tendency (performance on very hard questions)
        hard_responses = responses.filter(question__difficulty_level__gte=4)
        if hard_responses.exists():
            guessing_tendency = 1.0 - (hard_responses.filter(is_correct=True).count() / hard_responses.count())
            guessing_tendency = min(0.3, guessing_tendency)
        else:
            guessing_tendency = 0.15
        
        # Calculate consistency
        accuracies = []
        # Convert to list to avoid "Cannot filter a query once a slice has been taken"
        all_responses = list(responses.order_by('timestamp'))
        
        for i in range(0, len(all_responses), 5):
            chunk = all_responses[i:i+5]
            if not chunk:
                continue
            correct_in_chunk = sum(1 for r in chunk if r.is_correct)
            chunk_accuracy = correct_in_chunk / len(chunk)
            accuracies.append(chunk_accuracy)
        
        consistency_score = 1.0 - np.std(accuracies) if len(accuracies) > 1 else 0.5
        
        # Update learning profile
        profile = request.user.learning_profile
        profile.initial_ability = final_ability
        profile.current_ability = final_ability
        profile.learning_speed = learning_speed
        profile.guessing_tendency = guessing_tendency
        profile.consistency_score = consistency_score
        profile.onboarding_completed_at = timezone.now()
        profile.save()
        
        # Mark session as complete
        session.is_active = False
        session.completed_at = timezone.now()
        session.total_score = (session.correct_answers / responses.count()) * 100
        session.save()
        
        # Determine recommended starting level
        if final_ability < -0.5:
            recommended_level = "Easy"
        elif final_ability < 0.5:
            recommended_level = "Medium"
        else:
            recommended_level = "Hard"
        
        # Prepare stats for report
        stats = {
            'completed_at': session.completed_at,
            'final_ability': round(final_ability, 3),
            'learning_speed': round(learning_speed, 3),
            'guessing_tendency': round(guessing_tendency, 3),
            'consistency_score': round(consistency_score, 3),
            'recommended_starting_level': recommended_level,
            'total_questions': responses.count(),
            'correct_answers': session.correct_answers,
            'accuracy': round((session.correct_answers / responses.count()) * 100, 2)
        }

        # Award Badge: AI Diagnostic Pioneer
        Achievement.objects.get_or_create(
            user=request.user,
            achievement_type='diagnostic_complete',
            defaults={
                'title': 'AI Diagnostic Pioneer',
                'description': 'Completed the initial Learning DNA diagnostic assessment.',
                'icon_type': 'zap' # Using zap icon for pioneer
            }
        )

        # Create In-App Notification
        Notification.objects.create(
            user=request.user,
            title="Diagnostic Test Complete",
            message=f"You have completed your Learning DNA diagnostic test. Your ability score is {stats['final_ability']} and recommended level is {stats['recommended_starting_level']}.",
            notification_type='general', # Using general for now
            related_object_id=session.id,
            related_object_type='diagnostic_session'
        )

        # Send report email asynchronously
        try:
            email_thread = threading.Thread(
                target=send_diagnostic_report_email,
                args=(request.user, profile, stats)
            )
            email_thread.start()
        except Exception as e:
            print(f"Failed to send email: {e}")
        
        return Response({
            'status': 'success',
            'final_ability': round(final_ability, 3),
            'learning_speed': round(learning_speed, 3),
            'guessing_tendency': round(guessing_tendency, 3),
            'consistency_score': round(consistency_score, 3),
            'recommended_starting_level': recommended_level,
            'profile_updated': True,
            'total_questions': responses.count(),
            'correct_answers': session.correct_answers,
            'accuracy': round((session.correct_answers / responses.count()) * 100, 2)
        }, status=status.HTTP_200_OK)
    
    except QuizSession.DoesNotExist:
        return Response({
            'status': 'error',
            'message': 'Invalid session ID'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_learning_profile(request):
    """Get user's learning profile"""
    if not hasattr(request.user, 'learning_profile'):
        return Response({
            'status': 'error',
            'message': 'Learning profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    serializer = LearningProfileSerializer(request.user.learning_profile)
    return Response({
        'status': 'success',
        'profile': serializer.data
    }, status=status.HTTP_200_OK)


from django.http import HttpResponse
from utils.report_generator import generate_diagnostic_report_pdf

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_diagnostic_report(request):
    """
    Download the Learning DNA report as PDF
    GET /api/users/diagnostic-test/report/
    """
    print(f"DEBUG: download_diagnostic_report called for user {request.user.username}")
    try:
        if not hasattr(request.user, 'learning_profile'):
             return Response({
                 'status': 'error',
                 'error_code': 'NO_PROFILE',
                 'message': 'No learning profile found. Please complete your onboarding.'
             }, status=status.HTTP_404_NOT_FOUND)
        
        profile = request.user.learning_profile
        
        # Find the completed diagnostic session
        # Use case-insensitive title matching and check for both completed and most recent if many exist
        session = QuizSession.objects.filter(
            user=request.user, 
            quiz__title__iexact="Diagnostic Test",
            completed_at__isnull=False
        ).order_by('-completed_at').first()

        # Fallback: Find the most recent session for a quiz marked as diagnostic/total_questions matching diagnostic
        if not session:
             session = QuizSession.objects.filter(
                 user=request.user,
                 quiz__is_adaptive=True,
                 completed_at__isnull=False
             ).order_by('-completed_at').first()

        if not session:
            return Response({
                'status': 'error',
                'error_code': 'NO_SESSION',
                'message': 'No completed diagnostic test found. Please finish the diagnostic test first.'
            }, status=status.HTTP_404_NOT_FOUND)

        # Reconstruct stats (consistent with complete_diagnostic_test logic)
        responses = QuizResponse.objects.filter(session=session)
        
        # Determine recommended level
        if profile.current_ability < -0.5:
             recommended = "Easy"
        elif profile.current_ability < 0.5:
             recommended = "Medium"
        else:
             recommended = "Hard"

        stats = {
            'completed_at': session.completed_at,
            'final_ability': round(profile.current_ability, 3),
            'learning_speed': round(profile.learning_speed, 3),
            'guessing_tendency': round(profile.guessing_tendency, 3),
            'consistency_score': round(profile.consistency_score, 3),
            'recommended_starting_level': recommended,
            'total_questions': responses.count(),
            'correct_answers': session.correct_answers,
            'accuracy': round((session.correct_answers / responses.count() * 100) if responses.count() else 0, 2)
        }

        pdf = generate_diagnostic_report_pdf(request.user, profile, stats)
        
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="Learning_DNA_Report.pdf"'
        return response

    except Exception as e:
        print(f"Report download error: {e}")
        return Response({
            'status': 'error',
            'message': f'Failed to generate report: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
