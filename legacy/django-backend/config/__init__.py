
import pymysql
pymysql.version_info = (2, 2, 1, 'final', 0)
pymysql.install_as_MySQLdb()

# Without this import, config/celery.py's `app.config_from_object(...)` never
# runs — Celery's `current_app` and every `@shared_task` then bind to an
# auto-created, unconfigured default app (wrong broker, task_always_eager
# always False) instead of the one built from Django settings.
from .celery import app as celery_app

__all__ = ('celery_app',)
