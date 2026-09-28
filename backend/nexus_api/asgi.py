"""ASGI entry point, for servers such as uvicorn: `uvicorn nexus_api.asgi:application --port 8100`."""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nexus_api.settings")
application = get_asgi_application()
