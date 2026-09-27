import json
import threading
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response

from .models import AcademicSubject, SyllabusUpload, SyllabusRoadmap
from .serializers import (
    AcademicSubjectSerializer,
    SyllabusUploadSerializer,
    SyllabusRoadmapSerializer,
)
from .tasks import extract_syllabus_task


# ─────────────────────────────────────────────
#  Academic Subjects
# ─────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def subject_list(request):
    """List all subjects for the current user, or create a new one."""
    if request.method == 'GET':
        subjects = AcademicSubject.objects.filter(user=request.user, is_active=True)
        return Response(AcademicSubjectSerializer(subjects, many=True).data)

    serializer = AcademicSubjectSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def subject_detail(request, subject_id):
    """Retrieve, update, or soft-delete a subject."""
    try:
        subject = AcademicSubject.objects.get(id=subject_id, user=request.user)
    except AcademicSubject.DoesNotExist:
        return Response({'error': 'Subject not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(AcademicSubjectSerializer(subject).data)

    if request.method == 'PATCH':
        serializer = AcademicSubjectSerializer(subject, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # DELETE — soft delete
    subject.is_active = False
    subject.save(update_fields=['is_active'])
    return Response({'message': 'Subject removed.'}, status=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────
#  Syllabus Upload + AI Extraction
# ─────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def syllabus_upload(request):
    """
    Upload a syllabus PDF/image for a subject.
    Triggers async AI extraction immediately after saving.
    """
    file = request.FILES.get('file')
    subject_name = request.data.get('subject_name', '').strip()
    subject_id = request.data.get('subject_id', None)

    if not file:
        return Response({'error': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)
    if not subject_name:
        return Response({'error': 'subject_name is required.'}, status=status.HTTP_400_BAD_REQUEST)

    # Resolve subject FK if provided
    subject = None
    if subject_id:
        try:
            subject = AcademicSubject.objects.get(id=subject_id, user=request.user)
        except AcademicSubject.DoesNotExist:
            pass

    ext = file.name.rsplit('.', 1)[-1].lower() if '.' in file.name else ''
    upload = SyllabusUpload.objects.create(
        user=request.user,
        subject=subject,
        subject_name=subject_name,
        file=file,
        original_filename=file.name,
        file_type=ext,
        status='pending',
    )

    # Start extraction in background thread (no Celery required for MVP)
    thread = threading.Thread(target=extract_syllabus_task, args=(upload.id,), daemon=True)
    thread.start()

    return Response({
        'upload_id': upload.id,
        'status': 'pending',
        'message': 'Syllabus uploaded. AI extraction started.',
    }, status=status.HTTP_202_ACCEPTED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def syllabus_status(request, upload_id):
    """Poll extraction progress."""
    try:
        upload = SyllabusUpload.objects.get(id=upload_id, user=request.user)
    except SyllabusUpload.DoesNotExist:
        return Response({'error': 'Upload not found.'}, status=status.HTTP_404_NOT_FOUND)

    response = {
        'upload_id': upload.id,
        'status': upload.status,
        'subject_name': upload.subject_name,
    }
    if upload.status == 'error':
        response['error_message'] = upload.error_message
    if upload.status == 'done':
        try:
            roadmap = upload.roadmap
            response['roadmap_id'] = roadmap.id
            response['is_confirmed'] = roadmap.is_confirmed
            response['total_units'] = roadmap.total_units
            response['total_topics'] = roadmap.total_topics
        except SyllabusRoadmap.DoesNotExist:
            pass
    return Response(response)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def roadmap_detail(request, upload_id):
    """Get the full structured roadmap for a completed upload."""
    try:
        upload = SyllabusUpload.objects.get(id=upload_id, user=request.user)
        roadmap = upload.roadmap
    except (SyllabusUpload.DoesNotExist, SyllabusRoadmap.DoesNotExist):
        return Response({'error': 'Roadmap not found.'}, status=status.HTTP_404_NOT_FOUND)

    return Response(SyllabusRoadmapSerializer(roadmap).data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def roadmap_edit(request, upload_id):
    """Student edits the roadmap JSON before confirming."""
    try:
        upload = SyllabusUpload.objects.get(id=upload_id, user=request.user)
        roadmap = upload.roadmap
    except (SyllabusUpload.DoesNotExist, SyllabusRoadmap.DoesNotExist):
        return Response({'error': 'Roadmap not found.'}, status=status.HTTP_404_NOT_FOUND)

    if roadmap.is_confirmed:
        return Response({'error': 'Cannot edit a confirmed roadmap.'}, status=status.HTTP_400_BAD_REQUEST)

    new_json = request.data.get('roadmap_json')
    if new_json is None:
        return Response({'error': 'roadmap_json is required.'}, status=status.HTTP_400_BAD_REQUEST)

    roadmap.roadmap_json = new_json
    roadmap.save(update_fields=['roadmap_json', 'updated_at'])
    roadmap.compute_stats()
    return Response(SyllabusRoadmapSerializer(roadmap).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def roadmap_confirm(request, upload_id):
    """
    Student confirms the roadmap — makes it authoritative.
    Creates TopicMastery records for each topic in evaluator_agent.
    """
    try:
        upload = SyllabusUpload.objects.get(id=upload_id, user=request.user)
        roadmap = upload.roadmap
    except (SyllabusUpload.DoesNotExist, SyllabusRoadmap.DoesNotExist):
        return Response({'error': 'Roadmap not found.'}, status=status.HTTP_404_NOT_FOUND)

    if roadmap.is_confirmed:
        return Response({'message': 'Already confirmed.', 'roadmap_id': roadmap.id})

    roadmap.is_confirmed = True
    roadmap.confirmed_at = timezone.now()
    roadmap.save(update_fields=['is_confirmed', 'confirmed_at'])

    # Seed TopicMastery records for every topic
    _seed_topic_masteries(request.user, roadmap)

    # Update user onboarding step
    user = request.user
    if user.onboarding_step < 3:
        user.onboarding_step = 3
        user.save(update_fields=['onboarding_step'])

    return Response({
        'message': 'Roadmap confirmed. Learning roadmap is now active.',
        'roadmap_id': roadmap.id,
        'total_topics': roadmap.total_topics,
    })


def _seed_topic_masteries(user, roadmap):
    """Create TopicMastery records for every topic in the confirmed roadmap."""
    try:
        from evaluator_agent.models import TopicMastery
    except ImportError:
        return

    subject = roadmap.subject
    if not subject:
        return

    units = roadmap.roadmap_json.get('units', [])
    for unit in units:
        unit_name = unit.get('name', '')
        for topic in unit.get('topics', []):
            topic_name = topic.get('name', '')
            if topic_name:
                TopicMastery.objects.get_or_create(
                    user=user,
                    subject=subject,
                    unit_name=unit_name,
                    topic_name=topic_name,
                    defaults={
                        'subtopics': topic.get('subtopics', []),
                        'lab_exercises': topic.get('lab', []),
                    }
                )
