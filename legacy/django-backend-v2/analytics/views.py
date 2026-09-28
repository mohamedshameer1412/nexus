from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Avg, Count, Q
from quiz.models import QuizSession, Question
from quiz.models import Response as QuizResponse
from datetime import datetime, timedelta
import statistics


class AnalyticsViewSet(viewsets.ViewSet):
    """ML-powered analytics for student performance"""
    permission_classes = [permissions.IsAuthenticated]
    
    def _get_target_user(self, request):
        user = request.user
        student_id = request.query_params.get('student_id')
        
        if student_id and student_id != str(user.id):
            # Check permission
            if user.role == 'teacher':
                from users.models import Classroom
                if not Classroom.objects.filter(
                    Q(teacher=user) | Q(co_teachers=user),
                    students__id=student_id
                ).exists():
                    return None, "You do not have permission to view this student's analytics"
            else:
                return None, "Unauthorized"
            
            from users.models import User
            try:
                target_user = User.objects.get(id=student_id)
                return target_user, None
            except User.DoesNotExist:
                return None, "Student not found"

        return user, None

    @action(detail=False, methods=['get'], url_path='dashboard')
    def dashboard(self, request):
        """Get student dashboard with overall statistics"""
        user, error = self._get_target_user(request)
        if error:
            return Response({'error': error}, status=403 if "permission" in error.lower() else 400)
        
        # Get all sessions for this user
        sessions = QuizSession.objects.filter(user=user, is_active=False)
        
        if not sessions.exists():
            return Response({
                'total_sessions': 0,
                'average_score': 0,
                'total_questions_answered': 0,
                'time_spent_minutes': 0,
                'recent_sessions': []
            })
        
        # Calculate statistics
        total_sessions = sessions.count()
        avg_score = sessions.aggregate(Avg('total_score'))['total_score__avg'] or 0
        
        # Total questions answered
        total_questions = QuizResponse.objects.filter(
            session__user=user
        ).count()
        
        # Total time spent (sum of all session durations)
        total_time = 0
        for session in sessions:
            if session.started_at and session.completed_at:
                duration = (session.completed_at - session.started_at).total_seconds() / 60
                total_time += duration
        
        # Recent sessions (last 5)
        recent_sessions = []
        for session in sessions.order_by('-completed_at')[:5]:
            recent_sessions.append({
                'id': str(session.id),
                'quiz_title': session.quiz.title,
                'score': session.total_score,
                'completed_at': session.completed_at.isoformat() if session.completed_at else None
            })
        
        return Response({
            'total_sessions': total_sessions,
            'average_score': round(avg_score, 2),
            'total_questions_answered': total_questions,
            'time_spent_minutes': round(total_time, 2),
            'recent_sessions': recent_sessions
        })
    
    @action(detail=False, methods=['get'], url_path='performance-trends')
    def performance_trends(self, request):
        """Get performance trends over time (ML-powered)"""
        user, error = self._get_target_user(request)
        if error:
            return Response({'error': error}, status=400)
        
        # Get completed sessions ordered by date
        sessions = QuizSession.objects.filter(
            user=user,
            is_active=False,
            completed_at__isnull=False
        ).order_by('completed_at')
        
        if sessions.count() < 2:
            return Response({
                'message': 'Need at least 2 completed sessions for trend analysis',
                'trends': [],
                'overall_trend': 'insufficient_data'
            })
        
        # Build trend data
        trends = []
        scores = []
        
        for session in sessions:
            trends.append({
                'date': session.completed_at.date().isoformat(),
                'score': session.total_score,
                'quiz': session.quiz.title
            })
            scores.append(session.total_score)
        
        # Calculate trend direction using simple linear regression
        if len(scores) >= 3:
            # Calculate slope
            n = len(scores)
            x_values = list(range(n))
            x_mean = sum(x_values) / n
            y_mean = sum(scores) / n
            
            numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, scores))
            denominator = sum((x - x_mean) ** 2 for x in x_values)
            
            slope = numerator / denominator if denominator != 0 else 0
            
            if slope > 1:
                trend_direction = 'improving'
            elif slope < -1:
                trend_direction = 'declining'
            else:
                trend_direction = 'stable'
        else:
            # Simple comparison for 2 sessions
            if scores[-1] > scores[0]:
                trend_direction = 'improving'
            elif scores[-1] < scores[0]:
                trend_direction = 'declining'
            else:
                trend_direction = 'stable'
        
        return Response({
            'trends': trends,
            'overall_trend': trend_direction,
            'average_score': round(statistics.mean(scores), 2),
            'latest_score': scores[-1],
            'improvement': round(scores[-1] - scores[0], 2) if len(scores) >= 2 else 0
        })
    
    @action(detail=False, methods=['get'], url_path='weak-topics')
    def weak_topics(self, request):
        """Identify weak topics based on performance (ML-powered)"""
        user, error = self._get_target_user(request)
        if error:
            return Response({'error': error}, status=400)
        
        # Get all responses for this user
        responses = QuizResponse.objects.filter(
            session__user=user
        ).select_related('question', 'question__topic')
        
        if not responses.exists():
            return Response({
                'message': 'No quiz data available for analysis',
                'weak_topics': []
            })
            
        # --- ML Integration: Weak Topic Predictor ---
        try:
            from ml_engine.weak_topic_predictor import weak_topic_predictor
            from quiz.models import Topic
            
            all_topics = Topic.objects.all()
            
            # Get predictions for all topics
            predictions = weak_topic_predictor.predict_weak_topics(responses, all_topics)
            
            weak_topics = []
            for p in predictions:
                # Only include weak topics
                if p['is_weak'] or p['weakness_probability'] > 0.4:
                    weak_topics.append({
                        'topic_name': p['topic_name'],
                        'accuracy': round((1 - p['weakness_probability']) * 100, 1), # Inverse prob as mock accuracy
                        'questions_attempted': responses.filter(question__topic__id=p['topic_id']).count(),
                        'average_difficulty': 3, # Default
                        'recommendation': f"AI Analysis: {p['weakness_probability']*100:.0f}% probability of difficulty."
                    })
            
        except Exception as e:
            print(f"ML Prediction failed: {e}")
            # Fallback to simple heuristics
            topic_stats = {}
            for response in responses:
                if not response.question.topic: continue
                topic_id = str(response.question.topic.id)
                if topic_id not in topic_stats:
                    topic_stats[topic_id] = {
                        'topic_name': response.question.topic.name,
                        'total': 0, 'correct': 0
                    }
                topic_stats[topic_id]['total'] += 1
                if response.is_correct:
                    topic_stats[topic_id]['correct'] += 1
            
            weak_topics = []
            for t_id, stats in topic_stats.items():
                acc = (stats['correct'] / stats['total']) * 100
                if acc < 70:
                    weak_topics.append({
                        'topic_name': stats['topic_name'],
                        'accuracy': round(acc, 1),
                        'questions_attempted': stats['total'],
                        'average_difficulty': 0,
                        'recommendation': "Review basics."
                    })
        
        # Sort by accuracy (weakest first)
        weak_topics.sort(key=lambda x: x['accuracy'])
        
        return Response({
            'weak_topics': weak_topics,
            'total_topics_analyzed': all_topics.count(),
            'weak_topics_count': len(weak_topics)
        })
    
    @action(detail=False, methods=['get'], url_path='predict-performance')
    def predict_performance(self, request):
        """Predict future performance using ML"""
        user, error = self._get_target_user(request)
        if error:
            return Response({'error': error}, status=400)
        
        # Get recent sessions
        recent_sessions = QuizSession.objects.filter(
            user=user,
            is_active=False,
            completed_at__isnull=False
        ).order_by('-completed_at')[:10]
        
        if recent_sessions.count() < 3:
            return Response({
                'message': 'Need at least 3 completed sessions for prediction',
                'predicted_score': None,
                'confidence': 'low'
            })
            
        scores = [session.total_score for session in reversed(list(recent_sessions))]
        
        # --- ML Integration: Performance Predictor ---
        predicted_score = 0
        confidence = 'low'
        
        try:
            from ml_engine.performance_predictor import performance_predictor
            from quiz.models import Response as QuizResponse
            
            # Get user responses for feature extraction
            user_responses = QuizResponse.objects.filter(session__user=user)
            
            if user_responses.exists():
                features = performance_predictor.extract_features(user_responses)
                predicted_score = performance_predictor.predict(features)
                confidence = 'high' if performance_predictor.is_trained else 'medium' # Medium if using default heuristic inside predict
            else:
                # Fallback to simple average
                predicted_score = statistics.mean(scores[-3:])
                confidence = 'low'
                
        except Exception as e:
            print(f"ML Performance Prediction failed: {e}")
            # Fallback
            predicted_score = statistics.mean(scores[-3:])
            confidence = 'low'
            
        # Calculate trend for display
        if len(scores) >= 2:
            recent_trend = scores[-1] - scores[-2]
            if recent_trend > 5:
                trend = 'improving'
            elif recent_trend < -5:
                trend = 'declining'
            else:
                trend = 'stable'
        else:
            trend = 'unknown'
        
        # Calculate variance (consistency)
        variance = statistics.variance(scores) if len(scores) >= 2 else 0
        consistency = 'high' if variance < 100 else 'medium' if variance < 300 else 'low'
        
        return Response({
            'predicted_score': round(predicted_score, 2),
            'confidence': confidence,
            'current_average': round(statistics.mean(scores), 2),
            'recent_trend': trend,
            'consistency': consistency,
            'sessions_analyzed': len(scores),
            'recommendation': self._get_performance_recommendation(predicted_score, trend)
        })

    @action(detail=False, methods=['get'], url_path='quiz-results/(?P<quiz_id>[^/.]+)')
    def quiz_results(self, request, quiz_id=None):
        """Get aggregated results for a specific quiz (Teacher View)"""
        if request.user.role != 'teacher':
             from rest_framework import status
             return Response({'error': 'Only teachers can view aggregate results'}, status=status.HTTP_403_FORBIDDEN)
        
        # Get all completed sessions for this quiz
        sessions = QuizSession.objects.filter(
            quiz_id=quiz_id,
            completed_at__isnull=False
        ).select_related('user').order_by('-completed_at')
        
        results = []
        for session in sessions:
            results.append({
                'session_id': session.id,
                'student_name': session.user.full_name,
                'student_email': session.user.email,
                'score': session.total_score,
                'accuracy': session.accuracy,
                'completed_at': session.completed_at,
                'time_taken': ((session.completed_at - session.started_at).total_seconds() / 60) if session.started_at else 0,
                'status': 'Completed'
            })
            
        return Response(results)
    
    @action(detail=True, methods=['get'], url_path='session-results')
    def session_results(self, request, pk=None):
        """Get detailed results for a specific quiz session"""
        from django.shortcuts import get_object_or_404
        
        # Permission check: similar to QuizSessionViewSet.get_queryset
        user = request.user
        session = get_object_or_404(QuizSession, id=pk)
        
        is_owner = session.user == user
        is_teacher = getattr(user, 'role', None) == 'teacher'
        is_staff = user.is_staff
        
        # If teacher, check if they have access to this student's classroom or the quiz
        has_teacher_access = False
        if is_teacher:
            from users.models import Classroom
            teacher_classrooms = Classroom.objects.filter(Q(teacher=user) | Q(co_teachers=user))
            classroom_ids = teacher_classrooms.values_list('id', flat=True)
            has_teacher_access = QuizSession.objects.filter(
                id=pk
            ).filter(
                Q(classroom_assignment__classroom_id__in=classroom_ids) |
                Q(quiz__created_by=user)
            ).exists()

        if not (is_owner or has_teacher_access or is_staff):
             from rest_framework import status
             return Response({"error": "You do not have permission to view these results"}, status=status.HTTP_403_FORBIDDEN)
        
        # Get all responses for this session
        responses = QuizResponse.objects.filter(session=session).select_related('question')
        
        # Build response data
        questions_data = []
        for response in responses:
            questions_data.append({
                'question_text': response.question.question_text,
                'selected_answer': response.selected_answer,
                'correct_answer': response.question.correct_answer,
                'is_correct': response.is_correct,
                'explanation': response.question.explanation,
                'response_time': response.response_time,
                'difficulty': response.question.difficulty_level,
                'topic_name': response.question.topic.name
            })
        
        return Response({
            'session_id': str(session.id),
            'quiz_title': session.quiz.title,
            'total_score': session.total_score if session.total_score > 0 else session.accuracy,
            'correct_answers': session.correct_answers,
            'incorrect_answers': session.incorrect_answers,
            'accuracy': session.accuracy,
            'started_at': session.started_at.isoformat() if session.started_at else None,
            'completed_at': session.completed_at.isoformat() if session.completed_at else None,
            'time_taken_minutes': ((session.completed_at - session.started_at).total_seconds() / 60) if session.started_at and session.completed_at else 0,
            'avg_response_time': session.avg_response_time,
            'detected_mindset': session.detected_mindset,
            'student_ability': session.student_ability,
            'behavior_score': session.behavior_score,
            'questions': questions_data
        })
    
    def _get_recommendation(self, accuracy, difficulty):
        """Get recommendation based on accuracy and difficulty"""
        if accuracy < 50:
            return "Focus on fundamentals. Start with easier questions and build confidence."
        elif accuracy < 70:
            return "Review the basics and practice more questions in this topic."
        else:
            return "Good progress! Try more challenging questions to improve further."
    
    def _get_performance_recommendation(self, predicted_score, trend):
        """Get recommendation based on predicted performance"""
        if predicted_score >= 80:
            if trend == 'improving':
                return "Excellent work! Keep up the momentum."
            else:
                return "Great performance! Maintain your study routine."
        elif predicted_score >= 60:
            if trend == 'declining':
                return "Your performance is slipping. Review recent topics and practice more."
            else:
                return "Good progress. Focus on weak areas to improve further."
        else:
            return "Need more practice. Focus on understanding concepts before attempting quizzes."
