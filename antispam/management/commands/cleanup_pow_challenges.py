from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from antispam.services import cleanup_expired_challenges


class Command(BaseCommand):
    help = "Remove expired/consumed proof-of-work challenges."

    def handle(self, *args: Any, **options: Any) -> None:
        deleted = cleanup_expired_challenges()
        self.stdout.write(
            self.style.SUCCESS(f"Removed {deleted} expired proof-of-work challenges.")
        )
