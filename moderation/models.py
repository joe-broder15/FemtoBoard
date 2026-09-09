from __future__ import annotations

from typing import ClassVar

from django.conf import settings
from django.db import models
from django.utils import timezone


class ReportCategory(models.TextChoices):
    SPAM = "SPAM", "Spam"
    ILLEGAL = "ILLEGAL", "Illegal content"
    RULE_VIOLATION = "RULE_VIOLATION", "Board rule violation"
    HARASSMENT = "HARASSMENT", "Harassment"
    OTHER = "OTHER", "Other"


class ReportStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    REVIEWING = "REVIEWING", "Reviewing"
    RESOLVED = "RESOLVED", "Resolved"
    REJECTED = "REJECTED", "Rejected"


class Ban(models.Model):
    """An exact-IP ban. ``board`` null means site-wide (design doc 47)."""

    ip_address = models.GenericIPAddressField()
    board = models.ForeignKey(
        "boards.Board", null=True, blank=True, on_delete=models.CASCADE, related_name="bans"
    )
    public_reason = models.CharField(max_length=256)
    internal_note = models.TextField(blank=True)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked = models.BooleanField(default=False)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["ip_address", "board"])]
        permissions = [
            ("issue_permanent_ban", "Can issue permanent bans"),
            ("search_ip", "Can perform unrestricted IP moderation search"),
        ]

    def __str__(self) -> str:
        scope = self.board.code if self.board else "site-wide"
        return f"Ban({self.ip_address}, {scope})"

    def is_permanent(self) -> bool:
        return self.expires_at is None

    def is_active(self) -> bool:
        if self.revoked:
            return False
        return self.expires_at is None or self.expires_at > timezone.now()

    def applies_to_board(self, board_code: str) -> bool:
        return self.board_id is None or self.board.code == board_code  # type: ignore[union-attr]


class Report(models.Model):
    post = models.ForeignKey("posts.Post", on_delete=models.CASCADE, related_name="reports")
    category = models.CharField(max_length=32, choices=ReportCategory.choices)
    explanation = models.CharField(max_length=500, blank=True)
    reporter_ip = models.GenericIPAddressField()
    status = models.CharField(
        max_length=16, choices=ReportStatus.choices, default=ReportStatus.OPEN
    )
    internal_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering: ClassVar[list[str]] = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"])]
        permissions = [
            ("resolve_report", "Can review and resolve reports"),
        ]

    def __str__(self) -> str:
        return f"Report(post={self.post_id}, {self.category})"


class ModerationAction(models.Model):
    """Append-only audit log (design doc section 54). Never editable or
    deletable through ordinary staff interfaces."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    verb = models.CharField(max_length=64)
    target = models.CharField(max_length=128)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering: ClassVar[list[str]] = ["-created_at"]
        indexes = [models.Index(fields=["verb", "created_at"]), models.Index(fields=["target"])]
        permissions = [
            ("view_ip_history", "Can view privileged IP moderation context"),
        ]

    def __str__(self) -> str:
        return f"{self.verb} {self.target}"
