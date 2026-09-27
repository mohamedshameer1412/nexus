import uuid
from django.db import models
from django.conf import settings


def syllabus_upload_path(instance, filename):
    return f"nexus/syllabus/{instance.user.id}/{filename}"


class AcademicSubject(models.Model):
    """One subject per user per semester — the anchor for all NEXUS activity."""
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='academic_subjects')

    name = models.CharField(max_length=200)            # e.g. "Data Structures"
    subject_code = models.CharField(max_length=30, blank=True, default='')
    department = models.CharField(max_length=100)
    semester = models.CharField(max_length=20)
    academic_year = models.CharField(max_length=20)

    end_exam_date = models.DateField(null=True, blank=True)
    target_percentage = models.IntegerField(default=75)
    available_hours_per_day = models.FloatField(default=2.0)

    # Aggregated mastery (updated after each assessment)
    overall_verified_mastery = models.FloatField(default=0.0)
    overall_self_mastery = models.FloatField(default=0.0)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'nexus_academic_subjects'
        ordering = ['name']

    def __str__(self):
        return f"{self.user.username} — {self.name} ({self.semester})"

    @property
    def days_to_exam(self):
        if self.end_exam_date:
            from django.utils import timezone
            delta = self.end_exam_date - timezone.now().date()
            return delta.days
        return None


class SyllabusUpload(models.Model):
    """Raw PDF/image uploaded by the student for AI extraction."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('error', 'Error'),
    ]

    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='syllabus_uploads')
    subject = models.ForeignKey(AcademicSubject, on_delete=models.CASCADE,
                                related_name='uploads', null=True, blank=True)
    subject_name = models.CharField(max_length=200)    # used before subject FK is set

    file = models.FileField(upload_to=syllabus_upload_path)
    original_filename = models.CharField(max_length=255, blank=True)
    file_type = models.CharField(max_length=10, blank=True)  # pdf, jpg, png

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True, default='')
    raw_extracted_text = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'nexus_syllabus_uploads'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} — {self.subject_name} ({self.status})"


class SyllabusRoadmap(models.Model):
    """
    AI-structured roadmap extracted from the syllabus upload.
    Must be confirmed by the student before becoming authoritative.

    roadmap_json shape:
    {
      "units": [
        {
          "name": "Unit I: Introduction",
          "topics": [
            {
              "name": "Arrays",
              "subtopics": ["1D Arrays", "2D Arrays", "Operations"],
              "lab": ["Array manipulation exercises"]
            }
          ]
        }
      ]
    }
    """
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36, editable=False)
    upload = models.OneToOneField(SyllabusUpload, on_delete=models.CASCADE,
                                  related_name='roadmap')
    subject = models.ForeignKey(AcademicSubject, on_delete=models.CASCADE,
                                related_name='roadmaps', null=True, blank=True)

    roadmap_json = models.JSONField(default=dict)

    # Student-confirmed = authoritative (used by all agents)
    is_confirmed = models.BooleanField(default=False)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    # Stats
    total_units = models.IntegerField(default=0)
    total_topics = models.IntegerField(default=0)
    total_subtopics = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'nexus_syllabus_roadmaps'

    def __str__(self):
        status = "✓ confirmed" if self.is_confirmed else "pending confirmation"
        return f"Roadmap: {self.upload.subject_name} ({status})"

    def compute_stats(self):
        """Recalculate unit/topic/subtopic counts from roadmap_json."""
        units = self.roadmap_json.get('units', [])
        self.total_units = len(units)
        self.total_topics = sum(len(u.get('topics', [])) for u in units)
        self.total_subtopics = sum(
            len(t.get('subtopics', []))
            for u in units
            for t in u.get('topics', [])
        )
        self.save(update_fields=['total_units', 'total_topics', 'total_subtopics'])
