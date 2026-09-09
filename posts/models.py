from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from django.db import models
from django.utils import timezone

if TYPE_CHECKING:
    from boards.models import Board


class TombstoneReason(models.TextChoices):
    USER = "USER", "Deleted by user"
    MODERATOR = "MODERATOR", "Deleted by moderator"


class Thread(models.Model):
    board = models.ForeignKey("boards.Board", on_delete=models.CASCADE, related_name="threads")
    created_at = models.DateTimeField(auto_now_add=True)
    bumped_at = models.DateTimeField(default=timezone.now)
    locked = models.BooleanField(default=False)
    stickied = models.BooleanField(default=False)
    stickied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["board", "bumped_at"]),
            models.Index(fields=["board", "stickied", "stickied_at"]),
        ]

    def __str__(self) -> str:
        return f"Thread({self.id}) /{self.board.code}/"

    def reply_count(self) -> int:
        return self.posts.filter(is_opening_post=False).count()

    def media_count(self) -> int:
        return self.posts.filter(media__isnull=False).count()

    def is_over_bump_limit(self) -> bool:
        """True once the thread has more replies than the board's bump
        limit. The reply that reaches the limit exactly still bumps;
        replies after it do not (design doc section 14)."""
        return self.reply_count() > self.board.bump_limit


class Post(models.Model):
    """A single post. The primary key doubles as the globally unique
    public post number (design doc section 20)."""

    thread = models.ForeignKey("posts.Thread", on_delete=models.CASCADE, related_name="posts")
    is_opening_post = models.BooleanField(default=False)

    subject = models.CharField(max_length=100, blank=True)
    body = models.TextField(max_length=4000, blank=True)
    display_name = models.CharField(max_length=64, blank=True)
    tripcode = models.CharField(max_length=16, blank=True)
    sage = models.BooleanField(default=False)

    deletion_password_hash = models.CharField(max_length=128, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    is_tombstone = models.BooleanField(default=False)
    tombstone_reason = models.CharField(max_length=16, choices=TombstoneReason.choices, blank=True)

    # Private moderation data. Never rendered publicly; scrubbed after
    # FEMTOBOARD_IP_RETENTION_DAYS (design doc section 46, 80.20).
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    ip_removed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering: ClassVar[list[str]] = ["id"]
        indexes = [
            models.Index(fields=["thread", "id"]),
            models.Index(fields=["ip_address", "created_at"]),
        ]
        # ``delete_post`` is intentionally not listed here: it's already
        # the model's built-in default permission. The rest are Post-level
        # actions taken against a post's thread.
        permissions = [
            ("delete_thread", "Can delete a thread"),
            ("lock_thread", "Can lock/unlock a thread"),
            ("sticky_thread", "Can sticky/unsticky a thread"),
        ]

    def __str__(self) -> str:
        return f"Post #{self.id}"

    @property
    def board(self) -> Board:
        return self.thread.board

    def display_identity(self) -> str:
        name = self.display_name or "Anonymous"
        if self.tripcode:
            return f"{name} {self.tripcode}"
        return name


class PostMedia(models.Model):
    class MediaType(models.TextChoices):
        IMAGE = "IMAGE", "Image"
        VIDEO = "VIDEO", "Video"

    post = models.OneToOneField("posts.Post", on_delete=models.CASCADE, related_name="media")
    media_type = models.CharField(max_length=8, choices=MediaType.choices)
    mime_type = models.CharField(max_length=32)
    file = models.FileField(upload_to="images/")
    thumbnail = models.FileField(upload_to="thumbs/", blank=True)
    original_filename = models.CharField(max_length=255)
    file_size_bytes = models.PositiveIntegerField()
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Media for post #{self.post_id}"


class PostReference(models.Model):
    """A same-board ``>>1234`` reference (design doc section 21-22)."""

    source_post = models.ForeignKey(
        "posts.Post", on_delete=models.CASCADE, related_name="references_made"
    )
    target_post = models.ForeignKey(
        "posts.Post", on_delete=models.CASCADE, related_name="referenced_by"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source_post", "target_post"], name="posts_reference_unique"
            )
        ]
        indexes = [models.Index(fields=["target_post"])]

    def __str__(self) -> str:
        return f"{self.source_post_id} -> {self.target_post_id}"
