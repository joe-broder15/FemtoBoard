"""Settings used by the pytest suite and by mypy/django-stubs."""

from __future__ import annotations

import tempfile
from pathlib import Path

from .base import *  # noqa: F403

DEBUG = False
SECRET_KEY = "test-secret-key"  # noqa: S105
ALLOWED_HOSTS: list[str] = ["testserver"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

_TEST_MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="femtoboard-test-media-"))
MEDIA_ROOT = _TEST_MEDIA_ROOT
MEDIA_URL = "/media/"

FEMTOBOARD_TRIPCODE_KEY = "test-tripcode-key"  # noqa: S105

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
