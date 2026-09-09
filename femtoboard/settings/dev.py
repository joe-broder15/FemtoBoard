"""Local development settings. Never used in production."""

from __future__ import annotations

from .base import *  # noqa: F403
from .base import BASE_DIR

DEBUG = True
SECRET_KEY = "dev-only-insecure-secret-key-do-not-deploy"  # noqa: S105
ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "data" / "db" / "femtoboard.sqlite3",
        "OPTIONS": {
            "init_command": "PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;",
        },
    }
}

MEDIA_ROOT = BASE_DIR / "data" / "media"
MEDIA_URL = "/media/"

FEMTOBOARD_TRIPCODE_KEY = "dev-only-insecure-tripcode-key"  # noqa: S105

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
