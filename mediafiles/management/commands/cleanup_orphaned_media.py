"""Remove media/thumbnail files on disk with no corresponding database
row (e.g. left behind by an interrupted upload)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand

from posts.models import PostMedia


class Command(BaseCommand):
    help = "Delete media/thumbnail files not referenced by any PostMedia row."

    def handle(self, *args: Any, **options: Any) -> None:
        known: set[str] = set()
        for file_field, thumb_field in PostMedia.objects.values_list("file", "thumbnail"):
            if file_field:
                known.add(str(file_field))
            if thumb_field:
                known.add(str(thumb_field))

        media_root = Path(str(settings.MEDIA_ROOT))
        removed = 0
        for subdir in (
            settings.MEDIA_ROOT_IMAGES,
            settings.MEDIA_ROOT_VIDEOS,
            settings.MEDIA_ROOT_THUMBS,
        ):
            directory = media_root / subdir
            if not directory.is_dir():
                continue
            for path in directory.iterdir():
                if not path.is_file():
                    continue
                relative = f"{subdir}/{path.name}"
                if relative not in known:
                    path.unlink(missing_ok=True)
                    removed += 1

        self.stdout.write(self.style.SUCCESS(f"Removed {removed} orphaned media files."))
