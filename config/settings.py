import json
import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("SECRET_KEY", "unsafe-development-key-change-before-deploy")
DEBUG = os.environ.get("DEBUG", "true").lower() == "true"
if not DEBUG and (
    SECRET_KEY == "unsafe-development-key-change-before-deploy"
    or len(SECRET_KEY) < 50
):
    raise ImproperlyConfigured("Set a unique SECRET_KEY of at least 50 characters when DEBUG is false.")
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
    if host.strip()
]
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
if not DEBUG and (not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS):
    raise ImproperlyConfigured("Configure explicit ALLOWED_HOSTS when DEBUG is false.")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "accounts",
    "profiles",
    "opportunities",
    "matching",
    "applications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
if not DEBUG:
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASE_URL = os.environ.get("DATABASE_URL", "")
DATABASES = {
    "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600)
    if DATABASE_URL
    else {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}
}
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

CACHES = {
    "default": {
        "BACKEND": os.environ.get(
            "CACHE_BACKEND",
            "django.core.cache.backends.locmem.LocMemCache"
            if DEBUG
            else "django.core.cache.backends.db.DatabaseCache",
        ),
        "LOCATION": os.environ.get("CACHE_LOCATION", "opendoors-ai-cache"),
    }
}
if CACHES["default"]["BACKEND"] == "django.core.cache.backends.db.DatabaseCache":
    CACHES["default"]["LOCATION"] = os.environ.get("CACHE_TABLE", "django_cache")

EMAIL_ENABLED = os.environ.get("EMAIL_ENABLED", "false").lower() == "true"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "true").lower() == "true"
EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "false").lower() == "true"
EMAIL_TIMEOUT = max(1, int(os.environ.get("EMAIL_TIMEOUT", "15")))
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "OpenDoors AI <no-reply@localhost>")
EMAIL_BACKEND = (
    "django.core.mail.backends.console.EmailBackend"
    if DEBUG and not EMAIL_HOST
    else "django.core.mail.backends.smtp.EmailBackend"
)
if EMAIL_ENABLED and not DEBUG and not EMAIL_HOST:
    raise ImproperlyConfigured("Set EMAIL_HOST before enabling email in production.")
if EMAIL_USE_TLS and EMAIL_USE_SSL:
    raise ImproperlyConfigured("Use either EMAIL_USE_TLS or EMAIL_USE_SSL, not both.")
ACCOUNT_RATE_LIMIT_ATTEMPTS = max(1, int(os.environ.get("ACCOUNT_RATE_LIMIT_ATTEMPTS", "5")))
ACCOUNT_RATE_LIMIT_WINDOW_SECONDS = max(
    60, int(os.environ.get("ACCOUNT_RATE_LIMIT_WINDOW_SECONDS", "900"))
)
PASSWORD_RESET_TIMEOUT = max(60, int(os.environ.get("PASSWORD_RESET_TIMEOUT", "259200")))

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:dashboard"
LOGOUT_REDIRECT_URL = "accounts:home"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "media/"
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", str(BASE_DIR / "media"))).resolve()
FILE_STORAGE_BACKEND = os.environ.get(
    "FILE_STORAGE_BACKEND", "django.core.files.storage.FileSystemStorage"
)
try:
    FILE_STORAGE_OPTIONS = json.loads(os.environ.get("FILE_STORAGE_OPTIONS_JSON", "{}"))
except json.JSONDecodeError as error:
    raise ImproperlyConfigured("FILE_STORAGE_OPTIONS_JSON must be valid JSON.") from error
if FILE_STORAGE_BACKEND == "django.core.files.storage.FileSystemStorage":
    FILE_STORAGE_OPTIONS = {
        "location": str(MEDIA_ROOT),
        "base_url": None,
        **FILE_STORAGE_OPTIONS,
    }
STORAGES = {
    "default": {"BACKEND": FILE_STORAGE_BACKEND, "OPTIONS": FILE_STORAGE_OPTIONS},
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedStaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 12,
}

AI_ENABLED = os.environ.get("AI_ENABLED", "false").lower() == "true"
AI_PROVIDER = os.environ.get("AI_PROVIDER", "")
AI_API_KEY = os.environ.get("AI_API_KEY", "")
AI_MODEL = os.environ.get("AI_MODEL", "")
AI_BASE_URL = os.environ.get("AI_BASE_URL", "https://api.openai.com/v1")
AI_TIMEOUT_SECONDS = max(1, int(os.environ.get("AI_TIMEOUT_SECONDS", "30")))
AI_SITE_URL = os.environ.get("AI_SITE_URL", "")
AI_SITE_NAME = os.environ.get("AI_SITE_NAME", "OpenDoors AI")
OPPORTUNITY_FEEDS_JSON = os.environ.get("OPPORTUNITY_FEEDS_JSON", "[]")
TRUSTED_OPPORTUNITY_SOURCE_HOSTS = {
    host.strip().casefold()
    for host in os.environ.get("TRUSTED_OPPORTUNITY_SOURCE_HOSTS", "").split(",")
    if host.strip()
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
if not DEBUG:
    SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "true").lower() == "true"
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
