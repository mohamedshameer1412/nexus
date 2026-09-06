import uuid
from django.db import models
from django.conf import settings


def workspace_file_path(instance, filename):
    return f"nexus/workspace/{instance.workspace.user.id}/{filename}"


class SubjectWorkspace(models.Model):
    """One workspace per user per subject — the home for all subject activity."""
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='workspaces')
    subject = models.OneToOneField('syllabus.AcademicSubject', on_delete=models.CASCADE,
                                   related_name='workspace')

    # Aggregated stats
    overall_verified_mastery = models.FloatField(default=0.0)
    overall_self_mastery = models.FloatField(default=0.0)
    total_files = models.IntegerField(default=0)
    total_study_sessions = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'nexus_workspaces'
        ordering = ['-created_at']

    def __str__(self):
        return f"Workspace: {self.user.username} — {self.subject.name}"


class AcademicFile(models.Model):
    """
    Student-uploaded academic files: notes, PYQs, lab sheets, etc.
    AI auto-classifies each file by subject/unit/topic.
    """
    FILE_TYPE_CHOICES = [
        ('notes', 'Lecture Notes'),
        ('pyq', 'Previous Year Questions'),
        ('lab', 'Lab Sheet / Practical'),
        ('assessment', 'Internal Assessment'),
        ('reference', 'Reference Material'),
        ('other', 'Other'),
    ]

    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    workspace = models.ForeignKey(SubjectWorkspace, on_delete=models.CASCADE,
                                  related_name='files')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='academic_files')

    file = models.FileField(upload_to=workspace_file_path)
    original_filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=15, choices=FILE_TYPE_CHOICES, default='other')
    file_size_kb = models.FloatField(default=0.0)

    # AI Classification
    auto_unit = models.CharField(max_length=200, blank=True, default='')
    auto_topic = models.CharField(max_length=200, blank=True, default='')
    classification_confidence = models.FloatField(default=0.0)
    classification_done = models.BooleanField(default=False)

    # Extracted text (for Tutor Agent context)
    extracted_text = models.TextField(blank=True, default='')
    text_extracted = models.BooleanField(default=False)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'nexus_academic_files'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.original_filename} → {self.workspace.subject.name}"
