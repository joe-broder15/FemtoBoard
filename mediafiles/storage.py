"""Server-generated media paths (design doc sections 42, 80.11).

The uploaded filename is never used to construct a path -- only a random,
collision-resistant identifier the server generates itself. Callers must
always use these helpers instead of building paths by hand.
"""

from __future__ import annotations

import uuid
from pathlib import Path, PurePosixPath

from django.conf import settings
from django.core.files.storage import Storage, default_storage

_EXT_BY_MIME = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
    "video/webm": "webm",
}


def extension_for_mime(mime_type: str) -> str:
    return _EXT_BY_MIME.get(mime_type, "bin")


def generate_media_relative_path(mime_type: str) -> str:
    kind = settings.MEDIA_ROOT_VIDEOS if mime_type == "video/webm" else settings.MEDIA_ROOT_IMAGES
    name = f"{uuid.uuid4().hex}.{extension_for_mime(mime_type)}"
    return str(PurePosixPath(kind) / name)


def generate_thumbnail_relative_path() -> str:
    name = f"{uuid.uuid4().hex}.jpg"
    return str(PurePosixPath(settings.MEDIA_ROOT_THUMBS) / name)


def resolve_under_media_root(relative_path: str, storage: Storage = default_storage) -> str:
    """Resolve ``relative_path`` and verify it stays inside MEDIA_ROOT.

    Used before any filesystem delete so a corrupted or maliciously
    crafted stored path can never cause a deletion outside the media
    directory (design doc 80.11).
    """
    media_root = Path(str(settings.MEDIA_ROOT)).resolve()
    full_path = Path(storage.path(relative_path)).resolve()
    if media_root not in full_path.parents and full_path != media_root:
        raise ValueError(f"Refusing to touch path outside MEDIA_ROOT: {relative_path!r}")
    return str(full_path)
