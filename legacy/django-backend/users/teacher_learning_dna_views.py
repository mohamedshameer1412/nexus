"""
Teacher views for Learning DNA - Read-only access to student profiles
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import models
from django.db.models import Avg, Count

from users.models import LearningProfile, MasteryVector, User, Classroom
from users.serializers import LearningProfileSerializer, MasteryVectorSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_student_learning_profile(request, student_id):
    """
    Get student's learning profile (Teacher view)
    
    GET /api/users/teacher/student/{student_id}/learning-profile/
    
    Teachers can only view profiles of students in their classrooms
    """
    # Verify permissions
    has_permission = False
    
    if request.user.role == 'teacher':
        # Check if student is in any of teacher's classrooms
        has_permission = Classroom.objects.filter(
            models.Q(teacher=request.user) | models.Q(co_teachers=request.user),
            students__id=student_id
        ).exists()
    
    if not has_permission:
        return Response({
            'status': 'error',
            'message': 'You do not have permission to view this student\'s profile'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        student = User.objects.get(id=student_id, role='student')
        
        # Get learning profile
        if not hasattr(student, 'learning_profile'):
            return Response({
                'status': 'error',
                'message': 'Student has not completed onboarding yet'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = LearningProfileSerializer(student.learning_profile)
        
        return Response({
            'status': 'success',
            'student': {
                'id': student.id,
                'name': student.full_name,
                'email': student.email
            },
            'profile': serializer.data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_student_mastery_data(request, student_id):
    """
    Get student's mastery dashboard (Teacher view)
    
    GET /api/users/teacher/student/{student_id}/mastery/
    """
    try:
        student = get_object_or_404(User, id=student_id, role='student')
        
        has_permission = False
        
        if request.user.role == 'teacher':
            # Check if student is in any of teacher's classrooms
            is_teachers_student = Classroom.objects.filter(
                teacher=request.user,
                students=student
            ).exists() or Classroom.objects.filter(
                co_teachers=request.user,
                students=student
            ).exists()
            if is_teachers_student:
                has_permission = True
        
                
        if not has_permission:
            return Response({
                'status': 'error',
                'message': 'You do not have permission to view this student\'s mastery data'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get mastery vectors
        mastery_vectors = MasteryVector.objects.filter(user=student)
        
        if not mastery_vectors.exists():
            return Response({
                'status': 'success',
                'student': {
                    'id': student.id,
                    'name': student.full_name
                },
                'overall_mastery': 0.0,
                'total_concepts': 0,
                'mastered_concepts': 0,
                'weak_concepts': [],
                'strong_concepts': [],
                'mastery_by_subject': {}
            }, status=status.HTTP_200_OK)
        
        # Calculate metrics
        overall_mastery = mastery_vectors.aggregate(Avg('mastery_score'))['mastery_score__avg']
        mastered_count = mastery_vectors.filter(mastery_score__gte=0.7).count()
        weak_concepts = mastery_vectors.filter(mastery_score__lt=0.5).order_by('mastery_score')[:5]
        strong_concepts = mastery_vectors.filter(mastery_score__gte=0.8).order_by('-mastery_score')[:5]
        
        # Mastery by subject
        mastery_by_subject = {}
        for mv in mastery_vectors:
            subject = mv.concept_id.split('_')[0]
            if subject not in mastery_by_subject:
                mastery_by_subject[subject] = []
            mastery_by_subject[subject].append(mv.mastery_score)
        
        mastery_by_subject = {
            subject: round(sum(scores) / len(scores), 3)
            for subject, scores in mastery_by_subject.items()
        }
        
        return Response({
            'status': 'success',
            'student': {
                'id': student.id,
                'name': student.full_name,
                'email': student.email
            },
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
def get_classroom_mastery_analytics(request, classroom_id):
    """
    Get class-wide mastery analytics (Teacher view)
    
    GET /api/users/teacher/classroom/{classroom_id}/mastery-analytics/
    """
    # Verify user role
    if request.user.role not in ['teacher']:
        return Response({
            'status': 'error',
            'message': 'Only teachers can access this endpoint'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        classroom = get_object_or_404(Classroom, id=classroom_id)
        
        # Check permissions
        if request.user.role == 'teacher':
            if classroom.teacher != request.user and not classroom.co_teachers.filter(id=request.user.id).exists():
                return Response({
                    'status': 'error',
                    'message': 'You do not have permission to view this classroom\'s analytics'
                }, status=status.HTTP_403_FORBIDDEN)
            target_students = classroom.students.all()
        else:
            return Response({'status': 'error', 'message': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
        
        # Optimization: Get all mastery vectors for classroom students
        student_objs = target_students
        
        # For class metrics, we use all students
        class_masteries = []
        for student in classroom.students.all():
             mv_avg = MasteryVector.objects.filter(user=student).aggregate(Avg('mastery_score'))['mastery_score__avg']
             if mv_avg is not None:
                 class_masteries.append(mv_avg)
        
        class_average = sum(class_masteries) / len(class_masteries) if class_masteries else 0.0
        
        # Now prepare the specific student data for the response
        student_data = []
        for student in target_students:
            mastery_vectors = MasteryVector.objects.filter(user=student)
            mv_avg = mastery_vectors.aggregate(Avg('mastery_score'))['mastery_score__avg'] or 0.0
            student_data.append({
                'id': student.id,
                'name': student.full_name,
                'overall_mastery': round(mv_avg, 3),
                'total_concepts': mastery_vectors.count(),
                'mastered_concepts': mastery_vectors.filter(mastery_score__gte=0.7).count()
            })
        
        # Find common weak concepts (for class)
        analysis_students = classroom.students.all()

        concept_struggles = {}
        for student in analysis_students:
            weak_concepts = MasteryVector.objects.filter(
                user=student,
                mastery_score__lt=0.5
            )
            for concept in weak_concepts:
                if concept.concept_id not in concept_struggles:
                    concept_struggles[concept.concept_id] = 0
                concept_struggles[concept.concept_id] += 1
        
        common_weak_concepts = [
            {'concept': concept, 'students_struggling': count}
            for concept, count in sorted(concept_struggles.items(), key=lambda x: x[1], reverse=True)[:5]
        ]
        
        return Response({
            'status': 'success',
            'classroom': {
                'id': classroom.id,
                'name': classroom.name
            },
            'total_students': classroom.students.count(),
            'class_average_mastery': round(class_average, 3),
            'students': sorted(student_data, key=lambda x: x['overall_mastery']),
            'common_weak_concepts': common_weak_concepts
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
