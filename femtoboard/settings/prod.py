"""Production settings.

Every value that would be unsafe to leave at a framework default is set
explicitly here. Required secrets and configuration are read eagerly at
import time so a missing value fails application startup instead of
silently degrading security (design doc section 80.1).
"""

from __future__ import annotations

import os
from pathlib import Path

from femtoboard.runtime_secrets import read_secret

from .base import *  # noqa: F403

DEBUG = False

SECRET_KEY = read_secret("DJANGO_SECRET_KEY")

_allowed_hosts = os.environ.get("FEMTOBOARD_ALLOWED_HOSTS")
if not _allowed_hosts:
    raise RuntimeError("FEMTOBOARD_ALLOWED_HOSTS must be set in production")
ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts.split(",") if h.strip()]

_csrf_origins = os.environ.get("FEMTOBOARD_CSRF_TRUSTED_ORIGINS", "")
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins.split(",") if o.strip()]

_data_dir = Path(os.environ.get("FEMTOBOARD_DATA_DIR", "/var/lib/femtoboard"))

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": _data_dir / "db" / "femtoboard.sqlite3",
        "OPTIONS": {
            "init_command": "PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;",
        },
    }
}

MEDIA_ROOT = _data_dir / "media"
MEDIA_URL = "/media/"
STATIC_ROOT = _data_dir / "runtime" / "staticfiles"

FEMTOBOARD_TRIPCODE_KEY = read_secret("FEMTOBOARD_TRIPCODE_KEY")

FEMTOBOARD_TRUSTED_PROXY_COUNT = int(os.environ.get("FEMTOBOARD_TRUSTED_PROXY_COUNT", "1"))

# --- Transport security -----------------------------------------------
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # Django's own JS helper reads this; forms use {% csrf_token %}.
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 8

SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# The app server sits behind a reverse proxy that terminates TLS and sets
# this header; only trust it because the proxy is the sole network path in
# (see nix/module.nix, which binds the app to a unix socket / loopback).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
