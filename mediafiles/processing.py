"""Top-level media pipeline: validate -> process -> store.

This module is the only place that should call the lower-level
validation/ffmpeg/storage helpers together; posts.services calls
``process_media_upload`` and nothing else.
"""

from __future__ import annotations

import io
import os
import tempfile
from dataclasses import dataclass
from typing import Any, BinaryIO, cast

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import UploadedFile
from PIL import Image

from mediafiles import storage as media_storage
from mediafiles.ffmpeg import extract_poster_frame, probe_webm
from mediafiles.validation import (
    MediaValidationError,
    ValidatedImage,
    validate_image,
    validate_upload_basics,
)


@dataclass(frozen=True)
class ProcessedMedia:
    media_type: str  # "IMAGE" or "VIDEO"
    mime_type: str
    relative_path: str
    thumbnail_relative_path: str
    width: int | None
    height: int | None
    duration_seconds: float | None
    file_size_bytes: int


def _thumbnail_dim() -> int:
    dim: int = settings.FEMTOBOARD_THUMBNAIL_MAX_DIMENSION
    return dim


def _build_thumbnail_bytes(img: Image.Image) -> bytes:
    thumb = img.convert("RGB") if img.mode not in ("RGB", "L") else img.copy()
    thumb.thumbnail((_thumbnail_dim(), _thumbnail_dim()))
    buf = io.BytesIO()
    thumb.save(buf, format="JPEG", quality=82)
    return buf.getvalue()


def _strip_and_encode(img: Image.Image, mime_type: str) -> bytes:
    """Re-encode from raw pixel data only, discarding EXIF/text metadata
    (design doc 80.14). GIF is stored unmodified to preserve animation;
    GIF does not carry camera/device EXIF the way JPEG does."""
    clean = Image.frombytes(img.mode, img.size, img.tobytes())
    buf = io.BytesIO()
    if mime_type == "image/jpeg":
        clean.convert("RGB").save(buf, format="JPEG", quality=92)
    elif mime_type == "image/png":
        clean.save(buf, format="PNG")
    elif mime_type == "image/webp":
        clean.save(buf, format="WEBP", quality=90)
    else:  # pragma: no cover - guarded by caller
        raise MediaValidationError(f"Cannot re-encode {mime_type}")
    return buf.getvalue()


def _process_image(fileobj: BinaryIO, mime_type: str) -> tuple[bytes, bytes, ValidatedImage]:
    validated = validate_image(fileobj, mime_type)
    fileobj.seek(0)
    with Image.open(fileobj) as img:
        img.load()
        if mime_type == "image/gif":
            fileobj.seek(0)
            stored_bytes = fileobj.read()
        else:
            stored_bytes = _strip_and_encode(img, mime_type)
        thumb_bytes = _build_thumbnail_bytes(img)
    return stored_bytes, thumb_bytes, validated


def process_media_upload(
    uploaded_file: UploadedFile[Any],
    *,
    allowed_types: set[str],
    max_image_bytes: int,
    max_webm_bytes: int,
) -> ProcessedMedia:
    uploaded_file.seek(0)
    head = uploaded_file.read(64)
    uploaded_file.seek(0)
    file_size = uploaded_file.size or 0
    coarse_max = max(max_image_bytes, max_webm_bytes)
    mime_type = validate_upload_basics(
        file_size=file_size, head=head, allowed_types=allowed_types, max_bytes=coarse_max
    )

    if mime_type == "video/webm":
        if file_size > max_webm_bytes:
            raise MediaValidationError("WebM exceeds the maximum allowed size for this board")
        return _process_webm_upload(uploaded_file, mime_type, file_size)

    if file_size > max_image_bytes:
        raise MediaValidationError("Image exceeds the maximum allowed size for this board")
    stored_bytes, thumb_bytes, validated = _process_image(cast(BinaryIO, uploaded_file), mime_type)
    relative_path = media_storage.generate_media_relative_path(mime_type)
    thumb_relative_path = media_storage.generate_thumbnail_relative_path()
    default_storage.save(relative_path, ContentFile(stored_bytes))
    default_storage.save(thumb_relative_path, ContentFile(thumb_bytes))
    return ProcessedMedia(
        media_type="IMAGE",
        mime_type=mime_type,
        relative_path=relative_path,
        thumbnail_relative_path=thumb_relative_path,
        width=validated.width,
        height=validated.height,
        duration_seconds=None,
        file_size_bytes=len(stored_bytes),
    )


def _process_webm_upload(
    uploaded_file: UploadedFile[Any], mime_type: str, file_size: int
) -> ProcessedMedia:
    tmp_input_fd, tmp_input_path = tempfile.mkstemp(suffix=".webm")
    tmp_poster_fd, tmp_poster_path = tempfile.mkstemp(suffix=".jpg")
    os.close(tmp_poster_fd)
    try:
        with os.fdopen(tmp_input_fd, "wb") as tmp_input:
            uploaded_file.seek(0)
            for chunk in uploaded_file.chunks():
                tmp_input.write(chunk)

        metadata = probe_webm(tmp_input_path)
        extract_poster_frame(tmp_input_path, tmp_poster_path)

        with open(tmp_poster_path, "rb") as poster_fh:
            poster_validated = validate_image(poster_fh, "image/jpeg")
            poster_fh.seek(0)
            with Image.open(poster_fh) as poster_img:
                poster_img.load()
                thumb_bytes = _build_thumbnail_bytes(poster_img)

        relative_path = media_storage.generate_media_relative_path(mime_type)
        thumb_relative_path = media_storage.generate_thumbnail_relative_path()
        with open(tmp_input_path, "rb") as webm_fh:
            default_storage.save(relative_path, ContentFile(webm_fh.read()))
        default_storage.save(thumb_relative_path, ContentFile(thumb_bytes))

        return ProcessedMedia(
            media_type="VIDEO",
            mime_type=mime_type,
            relative_path=relative_path,
            thumbnail_relative_path=thumb_relative_path,
            width=metadata.width or poster_validated.width,
            height=metadata.height or poster_validated.height,
            duration_seconds=metadata.duration_seconds,
            file_size_bytes=file_size,
        )
    finally:
        for path in (tmp_input_path, tmp_poster_path):
            try:
                os.unlink(path)
            except OSError:
                pass


def delete_media_files(*, relative_path: str, thumbnail_relative_path: str) -> None:
    for rel_path in (relative_path, thumbnail_relative_path):
        if not rel_path:
            continue
        try:
            safe_path = media_storage.resolve_under_media_root(rel_path)
        except ValueError:
            continue
        if os.path.exists(safe_path):
            try:
                os.remove(safe_path)
            except OSError:
                pass
