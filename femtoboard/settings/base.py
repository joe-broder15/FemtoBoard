"""Settings shared by every environment.

Nothing here sets DEBUG, ALLOWED_HOSTS, or any other environment-specific
value: those live in dev.py / test.py / prod.py so that a missing
environment variable can never silently produce an insecure production
configuration (see design doc section 80.1).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import django_stubs_ext

# Lets typed generics like admin.ModelAdmin[Board] be subscripted at
# runtime (django-stubs types them as generic; Django itself is not).
django_stubs_ext.monkeypatch()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "boards",
    "antispam",
    "mediafiles",
    "posts",
    "moderation",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "femtoboard.security_middleware.SecurityHeadersMiddleware",
]

ROOT_URLCONF = "femtoboard.urls"

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
                "boards.context_processors.motd",
            ],
        },
    },
]

WSGI_APPLICATION = "femtoboard.wsgi.application"
ASGI_APPLICATION = "femtoboard.asgi.application"

AUTH_PASSWORD_VALIDATORS: list[dict[str, Any]] = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Argon2 is a memory-hard hasher; Django falls back down this list only for
# verifying legacy hashes, and always hashes new passwords with the first.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "moderation:dashboard"
LOGOUT_REDIRECT_URL = "accounts:login"

# Never let request bodies get logged wholesale; see settings LOGGING below
# in each environment file. Base logging config lives here since it does
# not itself leak secrets and is identical across environments except for
# verbosity.
LOGGING: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "default"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}

# ---------------------------------------------------------------------------
# Femtoboard application settings
# ---------------------------------------------------------------------------

# Media storage layout (design doc section 42).
MEDIA_ROOT_IMAGES = "images"
MEDIA_ROOT_VIDEOS = "videos"
MEDIA_ROOT_THUMBS = "thumbs"

# Global hard ceilings; per-board configuration may only be <= these.
FEMTOBOARD_MAX_IMAGE_BYTES = 10 * 1024 * 1024
FEMTOBOARD_MAX_WEBM_BYTES = 50 * 1024 * 1024
FEMTOBOARD_MAX_IMAGE_PIXELS = 40_000_000  # decompression-bomb guard
FEMTOBOARD_MAX_IMAGE_DIMENSION = 8000
FEMTOBOARD_MAX_WEBM_DURATION_SECONDS = 600
FEMTOBOARD_THUMBNAIL_MAX_DIMENSION = 400
FEMTOBOARD_FFMPEG_TIMEOUT_SECONDS = 20
FEMTOBOARD_FFMPEG_BINARY = "ffmpeg"
FEMTOBOARD_FFPROBE_BINARY = "ffprobe"

FEMTOBOARD_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
FEMTOBOARD_ALLOWED_VIDEO_TYPES = {"video/webm"}

# Post-level IP retention (design doc section 46).
FEMTOBOARD_IP_RETENTION_DAYS = 30

# Global minimum proof-of-work difficulty floor (section 80.17): board
# configuration can only ever raise difficulty above this, never below it.
FEMTOBOARD_MIN_POW_DIFFICULTY_BITS = 12
FEMTOBOARD_MAX_POW_DIFFICULTY_BITS = 28
FEMTOBOARD_POW_CHALLENGE_TTL_SECONDS = 600

# Trusted reverse proxy configuration (section 45 / 80.19). Empty by
# default (dev): no proxy is trusted and REMOTE_ADDR is used directly.
FEMTOBOARD_TRUSTED_PROXY_COUNT = 0

FEMTOBOARD_DEFAULT_THREADS_PER_PAGE = 15
FEMTOBOARD_DEFAULT_PREVIEW_REPLIES = 3

# Staff login abuse control (design doc 80.2). Site-wide, not per-board.
FEMTOBOARD_STAFF_LOGIN_RATE_LIMIT_COUNT = 10
FEMTOBOARD_STAFF_LOGIN_RATE_LIMIT_WINDOW_SECONDS = 300
