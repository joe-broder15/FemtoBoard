"""Anonymize post-level IP addresses past the retention window (design
doc sections 46, 80.20)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from posts.models import Post


class Command(BaseCommand):
    help = "Remove IP addresses from posts older than FEMTOBOARD_IP_RETENTION_DAYS."

    def handle(self, *args: Any, **options: Any) -> None:
        cutoff = timezone.now() - timedelta(days=settings.FEMTOBOARD_IP_RETENTION_DAYS)
        updated = Post.objects.filter(created_at__lt=cutoff, ip_address__isnull=False).update(
            ip_address=None, ip_removed_at=timezone.now()
        )
        self.stdout.write(self.style.SUCCESS(f"Anonymized IPs on {updated} posts."))
