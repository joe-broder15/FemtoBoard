from __future__ import annotations

import uuid

from django.db import models


class ActionType(models.TextChoices):
    THREAD = "THREAD", "Thread creation"
    REPLY = "REPLY", "Reply"
    REPORT = "REPORT", "Report"


class RateLimitCounter(models.Model):
    """A fixed-window counter for a (scope, key) pair.

    ``window_start`` is the window's epoch-aligned start time, so
    incrementing is a single atomic UPDATE (or INSERT on first use in a
    window) rather than a read-modify-write race (design doc 80.36).
    """

    scope = models.CharField(max_length=64)
    key = models.CharField(max_length=128)
    window_start = models.DateTimeField()
    count = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["scope", "key", "window_start"], name="antispam_ratelimit_unique_window"
            )
        ]
        indexes = [models.Index(fields=["scope", "key", "window_start"])]

    def __str__(self) -> str:
        return f"{self.scope}:{self.key}@{self.window_start.isoformat()}={self.count}"


class ProofOfWorkChallenge(models.Model):
    """A server-authoritative, single-use proof-of-work challenge.

    Verification state (``consumed_at``) lives in the database, so a
    challenge cannot be replayed: consumption is a conditional UPDATE
    that only succeeds once (design doc 80.17, 80.36).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    board = models.ForeignKey(
        "boards.Board", on_delete=models.CASCADE, related_name="pow_challenges"
    )
    action = models.CharField(max_length=16, choices=ActionType.choices)
    challenge = models.CharField(max_length=64)
    difficulty_bits = models.PositiveSmallIntegerField()
    client_ip = models.GenericIPAddressField()
    issued_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["board", "action", "expires_at"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self) -> str:
        return f"PoW[{self.id}] {self.board_id}/{self.action} bits={self.difficulty_bits}"
