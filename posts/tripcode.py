"""Tripcode derivation (design doc sections 6, 80.15).

The secret half of ``Name#secret`` is used only transiently, in-memory,
for the duration of the posting request. It is never written to the
database, logs, or any response after the derived tripcode is rendered
once at posting time.
"""

from __future__ import annotations

import base64
import hashlib
import hmac

from django.conf import settings

_DOMAIN = b"femtoboard-tripcode-v1"
_DISPLAY_LENGTH = 10


def split_name_and_secret(raw_name: str) -> tuple[str, str | None]:
    if "#" in raw_name:
        name, secret = raw_name.split("#", 1)
        secret = secret.strip()
        return name.strip(), (secret or None)
    return raw_name.strip(), None


def derive_tripcode(secret: str) -> str:
    key = settings.FEMTOBOARD_TRIPCODE_KEY.encode("utf-8")
    digest = hmac.new(key, _DOMAIN + b"|" + secret.encode("utf-8"), hashlib.sha256).digest()
    token = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return "!" + token[:_DISPLAY_LENGTH]
