
"""
Django settings for config project.

Development and production settings for BusinessHub.
"""

from pathlib import Path
import os

from dotenv import load_dotenv
import dj_database_url
from django.core.exceptions import ImproperlyConfigured


# =====================================================
# PROJECT PATHS AND ENVIRONMENT
# =====================================================

BASE_DIR = Path(__file__).resolve().parent.parent

# Load local environment variables from .env.
# On Render, environment variables can also be configured
# directly in the service's Environment settings.
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    """Read a boolean environment variable safely."""
    value = os.environ.get(name)

    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


IS_PRODUCTION = bool(
    os.environ.get("RENDER")
    or os.environ.get("RENDER_EXTERNAL_HOSTNAME")
    or os.environ.get("DJANGO_ENV", "").lower() == "production"
)


# =====================================================
# SECURITY
# =====================================================

SECRET_KEY = os.environ.get("SECRET_KEY")

if not SECRET_KEY:
    if IS_PRODUCTION:
        raise ImproperlyConfigured(
            "SECRET_KEY must be configured in the production "
            "environment before BusinessHub can start."
        )

    # Local development fallback only.
    # Configure a separate, private SECRET_KEY on Render.
    SECRET_KEY = (
        "local-development-only-key-not-for-production-"
        "businesshub-django-keep-this-private"
    )

DEBUG = env_bool("DEBUG", default=not IS_PRODUCTION)


ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
]

render_hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME")

if render_hostname:
    ALLOWED_HOSTS.append(render_hostname.strip())

additional_allowed_hosts = os.environ.get("ALLOWED_HOSTS", "")

for host in additional_allowed_hosts.split(","):
    host = host.strip()

    if host and host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(host)


# Optional extra trusted origins, separated by commas.
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CSRF_TRUSTED_ORIGINS", ""
    ).split(",")
    if origin.strip()
]


# Render terminates HTTPS at its proxy.
# This lets Django correctly recognize secure requests.
if IS_PRODUCTION:
    SECURE_PROXY_SSL_HEADER = (
        "HTTP_X_FORWARDED_PROTO",
        "https",
    )

    SECURE_SSL_REDIRECT = True

    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # Enable HSTS only in production, where the site should
    # be accessed over HTTPS.
    SECURE_HSTS_SECONDS = 31536000

    # Do not force HSTS onto every subdomain.
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False

else:
    SECURE_SSL_REDIRECT = False

    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False


SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"


# =====================================================
# APPLICATIONS
# =====================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "core",
]


# =====================================================
# MIDDLEWARE
# =====================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",

    "django.middleware.common.CommonMiddleware",

    "django.middleware.csrf.CsrfViewMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",

    "django.contrib.messages.middleware.MessageMiddleware",

    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# =====================================================
# URL CONFIGURATION
# =====================================================

ROOT_URLCONF = "config.urls"


# =====================================================
# TEMPLATES
# =====================================================

TEMPLATES = [
    {
        "BACKEND": (
            "django.template.backends.django.DjangoTemplates"
        ),

        "DIRS": [],

        "APP_DIRS": True,

        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",

                "django.contrib.auth.context_processors.auth",

                "django.contrib.messages.context_processors.messages",

                "core.context_processors.notifications",
            ],
        },
    },
]


# =====================================================
# WSGI
# =====================================================

WSGI_APPLICATION = "config.wsgi.application"


# =====================================================
# DATABASE
# =====================================================

DATABASES = {
    "default": dj_database_url.config(
        default="sqlite:///db.sqlite3",
        conn_max_age=600,
    )
}


# =====================================================
# PASSWORD VALIDATION
# =====================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },

    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },

    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },

    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# =====================================================
# INTERNATIONALIZATION
# =====================================================

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# =====================================================
# STATIC FILES
# =====================================================

STATIC_URL = "/static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {
        "BACKEND": (
            "django.core.files.storage.FileSystemStorage"
        ),
    },

    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage."
            "CompressedManifestStaticFilesStorage"
        ),
    },
}


# =====================================================
# MEDIA FILES
# =====================================================

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"


# =====================================================
# EMAIL — RESEND SMTP
# =====================================================



RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = os.environ.get(
    "EMAIL_HOST",
    "smtp.resend.com",
)

EMAIL_PORT = int(
    os.environ.get("EMAIL_PORT", "587")
)

EMAIL_HOST_USER = os.environ.get(
    "EMAIL_HOST_USER",
    "resend",
)

EMAIL_HOST_PASSWORD = os.environ.get(
    "EMAIL_HOST_PASSWORD",
    RESEND_API_KEY,
)

EMAIL_USE_TLS = env_bool(
    "EMAIL_USE_TLS",
    default=True,
)

EMAIL_USE_SSL = False

EMAIL_TIMEOUT = 20

DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL",
    "onboarding@resend.dev",
)

SERVER_EMAIL = DEFAULT_FROM_EMAIL
# =====================================================
# LOGIN
# =====================================================

LOGIN_URL = "/login/"


# =====================================================
# MTN MOMO COLLECTIONS
# PRESERVED — NO PAYMENT CHANGES
# =====================================================

MTN_BASE_URL = os.environ.get(
    "MTN_BASE_URL",
    "https://sandbox.momodeveloper.mtn.com",
)

MTN_TARGET_ENVIRONMENT = os.environ.get(
    "MTN_TARGET_ENVIRONMENT",
    "sandbox",
)

MTN_COLLECTION_PRIMARY_KEY = os.environ.get(
    "MTN_COLLECTION_PRIMARY_KEY",
    "",
)

MTN_API_USER = os.environ.get(
    "MTN_API_USER",
    "",
)

MTN_API_KEY = os.environ.get(
    "MTN_API_KEY",
    "",
)
