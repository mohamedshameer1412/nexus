from rest_framework import serializers
from .models import AcademicSubject, SyllabusUpload, SyllabusRoadmap


class AcademicSubjectSerializer(serializers.ModelSerializer):
    days_to_exam = serializers.ReadOnlyField()

    class Meta:
        model = AcademicSubject
        fields = [
            'id', 'name', 'subject_code', 'department', 'semester',
            'academic_year', 'end_exam_date', 'target_percentage',
            'available_hours_per_day', 'overall_verified_mastery',
            'overall_self_mastery', 'is_active', 'days_to_exam',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'overall_verified_mastery', 'overall_self_mastery',
                            'created_at', 'updated_at']


class SyllabusUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyllabusUpload
        fields = [
            'id', 'subject', 'subject_name', 'file', 'original_filename',
            'file_type', 'status', 'error_message', 'created_at',
        ]
        read_only_fields = ['id', 'status', 'error_message', 'created_at',
                            'original_filename', 'file_type']


class SyllabusRoadmapSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyllabusRoadmap
        fields = [
            'id', 'upload', 'subject', 'roadmap_json', 'is_confirmed',
            'confirmed_at', 'total_units', 'total_topics', 'total_subtopics',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'is_confirmed', 'confirmed_at',
                            'total_units', 'total_topics', 'total_subtopics',
                            'created_at', 'updated_at']
