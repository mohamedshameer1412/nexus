"""WSGI entry point: `python manage.py runserver 8100` in development, any WSGI server in production."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nexus_api.settings")
application = get_wsgi_application()
