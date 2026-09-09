"""Content-based media validation (design doc sections 39, 80.12, 80.13).

Never trusts file extensions or the browser-supplied Content-Type: the
actual file content is sniffed and, for images, fully decoded through
Pillow (which itself enforces the decompression-bomb ceiling configured
in mediafiles.apps.MediafilesConfig.ready).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO

from django.conf import settings
from PIL import Image, UnidentifiedImageError


class MediaValidationError(Exception):
    pass


_EXPECTED_PIL_FORMAT = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
    "image/gif": "GIF",
}


def sniff_mime_type(head: bytes) -> str | None:
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if head.startswith(b"RIFF") and head[8:12] == b"WEBP":
        return "image/webp"
    if head.startswith(b"\x1a\x45\xdf\xa3"):
        return "video/webm"
    return None


def validate_upload_basics(
    *, file_size: int, head: bytes, allowed_types: set[str], max_bytes: int
) -> str:
    """Sniff and validate the declared size/type. Returns the sniffed MIME
    type or raises MediaValidationError."""
    if file_size <= 0:
        raise MediaValidationError("Empty upload")
    if file_size > max_bytes:
        raise MediaValidationError("File exceeds the maximum allowed size")
    mime_type = sniff_mime_type(head)
    if mime_type is None:
        raise MediaValidationError("Unrecognized file type")
    if mime_type not in allowed_types:
        raise MediaValidationError(f"File type {mime_type} is not allowed on this board")
    return mime_type


@dataclass(frozen=True)
class ValidatedImage:
    width: int
    height: int


def validate_image(fileobj: BinaryIO, mime_type: str) -> ValidatedImage:
    """Fully decode the image, enforcing dimension/pixel-count ceilings.

    Raises MediaValidationError for malformed content, a format mismatch
    against the sniffed MIME type, or content over the configured limits.
    """
    expected_format = _EXPECTED_PIL_FORMAT.get(mime_type)
    if expected_format is None:
        raise MediaValidationError(f"Not an image type: {mime_type}")

    fileobj.seek(0)
    try:
        with Image.open(fileobj) as img:
            if img.format != expected_format:
                raise MediaValidationError(
                    f"File content ({img.format}) does not match declared type ({expected_format})"
                )
            width, height = img.size
            max_dim = settings.FEMTOBOARD_MAX_IMAGE_DIMENSION
            if width > max_dim or height > max_dim or width <= 0 or height <= 0:
                raise MediaValidationError("Image dimensions outside allowed range")
            img.load()
    except Image.DecompressionBombError as exc:
        raise MediaValidationError("Image exceeds the maximum decoded pixel count") from exc
    except UnidentifiedImageError as exc:
        raise MediaValidationError("Could not identify image content") from exc
    except OSError as exc:
        raise MediaValidationError("Malformed image content") from exc

    return ValidatedImage(width=width, height=height)
