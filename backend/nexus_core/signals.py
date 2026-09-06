"""
nexus_core/signals.py
Auto-creates a LearnerDigitalTwin whenever a new User is created.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import LearnerDigitalTwin


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_digital_twin(sender, instance, created, **kwargs):
    """Create a blank Digital Twin for every new user."""
    if created:
        LearnerDigitalTwin.objects.get_or_create(user=instance)
