from __future__ import annotations

from django.apps import AppConfig
from django.conf import settings


class MediafilesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mediafiles"

    def ready(self) -> None:
        from PIL import Image

        # Make Pillow itself refuse to decode past our decompression-bomb
        # ceiling (design doc 80.13), rather than relying on us checking
        # afterward.
        Image.MAX_IMAGE_PIXELS = settings.FEMTOBOARD_MAX_IMAGE_PIXELS
