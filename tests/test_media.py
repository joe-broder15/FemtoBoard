from __future__ import annotations

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from mediafiles.processing import process_media_upload
from mediafiles.validation import MediaValidationError

from .conftest import make_test_image

pytestmark = pytest.mark.django_db


def test_unsupported_media_type_rejected() -> None:
    upload = SimpleUploadedFile("shell.sh", b"#!/bin/sh\necho hi\n", content_type="text/plain")
    with pytest.raises(MediaValidationError):
        process_media_upload(
            upload,
            allowed_types={"image/jpeg", "video/webm"},
            max_image_bytes=10_000_000,
            max_webm_bytes=50_000_000,
        )


def test_extension_and_mime_spoofing_does_not_bypass_sniffing() -> None:
    # A text file renamed/declared as a jpeg: the browser-supplied
    # filename/content-type must not be trusted.
    upload = SimpleUploadedFile(
        "totally-a-photo.jpg", b"not actually a jpeg, just text", content_type="image/jpeg"
    )
    with pytest.raises(MediaValidationError):
        process_media_upload(
            upload,
            allowed_types={"image/jpeg"},
            max_image_bytes=10_000_000,
            max_webm_bytes=50_000_000,
        )


def test_oversized_image_rejected() -> None:
    upload = make_test_image()
    with pytest.raises(MediaValidationError):
        process_media_upload(
            upload,
            allowed_types={"image/jpeg"},
            max_image_bytes=10,  # smaller than any real JPEG
            max_webm_bytes=50_000_000,
        )


def test_disallowed_type_for_board_rejected() -> None:
    upload = make_test_image()
    with pytest.raises(MediaValidationError):
        process_media_upload(
            upload,
            allowed_types={"video/webm"},  # jpeg not allowed on this board
            max_image_bytes=10_000_000,
            max_webm_bytes=50_000_000,
        )


def test_generated_storage_path_ignores_original_filename() -> None:
    upload = SimpleUploadedFile(
        "../../etc/passwd.jpg", make_test_image().read(), content_type="image/jpeg"
    )
    result = process_media_upload(
        upload,
        allowed_types={"image/jpeg"},
        max_image_bytes=10_000_000,
        max_webm_bytes=50_000_000,
    )
    assert ".." not in result.relative_path
    assert "passwd" not in result.relative_path
    assert result.relative_path.startswith("images/")


def test_decompression_bomb_guard(settings) -> None:
    from PIL import Image

    settings.FEMTOBOARD_MAX_IMAGE_PIXELS = 100
    Image.MAX_IMAGE_PIXELS = 100
    import io

    buf = io.BytesIO()
    Image.new("RGB", (50, 50)).save(buf, format="PNG")
    buf.seek(0)
    upload = SimpleUploadedFile("bomb.png", buf.read(), content_type="image/png")
    with pytest.raises(MediaValidationError):
        process_media_upload(
            upload,
            allowed_types={"image/png"},
            max_image_bytes=10_000_000,
            max_webm_bytes=50_000_000,
        )
    Image.MAX_IMAGE_PIXELS = None
