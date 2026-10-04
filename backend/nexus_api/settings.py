"""NEXUS backend settings (Django).

Everything configurable comes from backend/.env (see .env.example); real environment variables win.
Database: PostgreSQL with DB_ENGINE=postgresql (Django's tables and the learning engine's, one database). SQLite by default
(the same file the learning engine uses); DB_ENGINE=mysql moves only Django's tables to MySQL/MariaDB.
"""
from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path

from slice.config import load_env
from studyhub import settings as engine

BASE_DIR = Path(__file__).resolve().parent.parent
if "pytest" not in sys.modules:          # tests must never pick up a real mail account or key from .env
    load_env(BASE_DIR / ".env")


def _flag(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


def _secret_key() -> str:
    """DJANGO_SECRET_KEY from the environment, else one generated once and kept in data/ (never in source)."""
    if os.environ.get("DJANGO_SECRET_KEY"):
        return os.environ["DJANGO_SECRET_KEY"]
    path = Path(engine.db_path()).resolve().parent / "django-secret.key"
    try:
        return path.read_text().strip()
    except FileNotFoundError:
        path.parent.mkdir(parents=True, exist_ok=True)
        key = secrets.token_urlsafe(50)
        path.write_text(key)
        return key


SECRET_KEY = _secret_key()
DEBUG = _flag("DJANGO_DEBUG", "1")
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"] + [h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
    "learning",
]

MIDDLEWARE = [
    "core.middleware.ApiMiddleware",          # size limit, security headers, JSON errors, non-API paths
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",   # Django admin only; the API has its own sessions
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",              # admin forms; API views check X-CSRF-Token themselves
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.audit.AuditMiddleware",
]

ROOT_URLCONF = "nexus_api.urls"
WSGI_APPLICATION = "nexus_api.wsgi.application"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]

if os.environ.get("DB_ENGINE", "sqlite").lower() in ("postgres", "postgresql"):
    from slice import pg as _pg
    _d = _pg.dsn()
    DATABASES = {"default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": _d["dbname"], "USER": _d["user"], "PASSWORD": _d["password"], "HOST": _d["host"], "PORT": _d["port"],
        "CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", "0")),   # 0: close with the request; a threaded server leaks idle ones
    }}
elif os.environ.get("DB_ENGINE", "sqlite").lower() == "mysql":
    DATABASES = {"default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ.get("DB_NAME", "nexus"),
        "USER": os.environ.get("DB_USER", "root"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "3306"),
        "OPTIONS": {"charset": "utf8mb4"},
    }}
    import pymysql
    pymysql.install_as_MySQLdb()
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(Path(engine.db_path()).resolve()),
                             "OPTIONS": {"timeout": 30}}}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LANGUAGE_CODE = "en"
LANGUAGES = [("en", "English"), ("hi", "Hindi")]
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "data" / "static"

# JSON bodies are small; uploads are files and are limited by STUDYHUB_MAX_UPLOAD_BYTES in the middleware.
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

SESSION_COOKIE_NAME = "nx_admin_session"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = engine.cookie_secure()
CSRF_COOKIE_SECURE = engine.cookie_secure()
X_FRAME_OPTIONS = "DENY"
# Served over HTTPS (STUDYHUB_COOKIE_SECURE=1): force HTTPS and tell browsers to keep using it.
if engine.cookie_secure():
    SECURE_SSL_REDIRECT = _flag("DJANGO_SSL_REDIRECT", "1")       # 0 when a proxy in front already redirects
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SECONDS", "31536000"))
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True

# Outgoing mail (the engine's mailer reads the same EMAIL_* variables).
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587") or 587)
EMAIL_USE_TLS = _flag("EMAIL_USE_TLS", "1")
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"nexus": {"handlers": ["console"], "level": "INFO"}},
}
