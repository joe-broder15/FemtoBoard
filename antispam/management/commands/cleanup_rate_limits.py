from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from antispam.services import cleanup_expired_rate_limits


class Command(BaseCommand):
    help = "Remove old rate-limit window counters."

    def handle(self, *args: Any, **options: Any) -> None:
        deleted = cleanup_expired_rate_limits()
        self.stdout.write(self.style.SUCCESS(f"Removed {deleted} expired rate-limit counters."))
