from django.apps import AppConfig


class NexusCoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "nexus_core"
    verbose_name = "NEXUS Core — Learner Digital Twin"

    def ready(self):
        import nexus_core.signals  # noqa: F401  — register signal handlers
