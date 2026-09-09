from __future__ import annotations

from typing import ClassVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models

_CODE_VALIDATOR = RegexValidator(
    regex=r"^[a-z0-9]{1,16}$",
    message="Board code must be lowercase letters/digits, 1-16 characters.",
)


class Board(models.Model):
    code = models.SlugField(max_length=16, unique=True, validators=[_CODE_VALIDATOR])
    name = models.CharField(max_length=64)
    description = models.CharField(max_length=256, blank=True)
    enabled = models.BooleanField(default=True)

    max_active_threads = models.PositiveIntegerField(default=100)
    threads_per_page = models.PositiveIntegerField(default=15)
    preview_reply_count = models.PositiveIntegerField(default=3)

    max_media_per_thread = models.PositiveIntegerField(default=150)
    max_post_length = models.PositiveIntegerField(default=2000)
    max_image_bytes = models.PositiveIntegerField(default=10 * 1024 * 1024)
    max_webm_bytes = models.PositiveIntegerField(default=50 * 1024 * 1024)

    allow_jpeg = models.BooleanField(default=True)
    allow_png = models.BooleanField(default=True)
    allow_webp = models.BooleanField(default=True)
    allow_gif = models.BooleanField(default=True)
    allow_webm = models.BooleanField(default=True)

    bump_limit = models.PositiveIntegerField(default=300)
    new_threads_enabled = models.BooleanField(default=True)
    tripcodes_enabled = models.BooleanField(default=True)

    motd = models.TextField(blank=True)

    thread_rate_limit_count = models.PositiveIntegerField(default=3)
    thread_rate_limit_window_seconds = models.PositiveIntegerField(default=600)
    reply_rate_limit_count = models.PositiveIntegerField(default=10)
    reply_rate_limit_window_seconds = models.PositiveIntegerField(default=300)

    report_rate_limit_count = models.PositiveIntegerField(default=5)
    report_rate_limit_window_seconds = models.PositiveIntegerField(default=600)
    report_duplicate_window_seconds = models.PositiveIntegerField(default=3600)
    report_requires_pow = models.BooleanField(default=False)
    pow_difficulty_report_bits = models.PositiveSmallIntegerField(default=12)

    pow_difficulty_thread_bits = models.PositiveSmallIntegerField(default=18)
    pow_difficulty_reply_bits = models.PositiveSmallIntegerField(default=14)
    pow_challenge_ttl_seconds = models.PositiveIntegerField(default=600)

    deletion_password_attempts_per_window = models.PositiveIntegerField(default=5)
    deletion_password_window_seconds = models.PositiveIntegerField(default=600)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering: ClassVar[list[str]] = ["code"]

    def __str__(self) -> str:
        return f"/{self.code}/"

    def clean(self) -> None:
        errors: dict[str, str] = {}
        if self.max_image_bytes > settings.FEMTOBOARD_MAX_IMAGE_BYTES:
            errors["max_image_bytes"] = (
                f"Cannot exceed global ceiling of {settings.FEMTOBOARD_MAX_IMAGE_BYTES} bytes."
            )
        if self.max_webm_bytes > settings.FEMTOBOARD_MAX_WEBM_BYTES:
            errors["max_webm_bytes"] = (
                f"Cannot exceed global ceiling of {settings.FEMTOBOARD_MAX_WEBM_BYTES} bytes."
            )
        for field_name in (
            "pow_difficulty_thread_bits",
            "pow_difficulty_reply_bits",
            "pow_difficulty_report_bits",
        ):
            bits = getattr(self, field_name)
            if not (
                settings.FEMTOBOARD_MIN_POW_DIFFICULTY_BITS
                <= bits
                <= settings.FEMTOBOARD_MAX_POW_DIFFICULTY_BITS
            ):
                errors[field_name] = (
                    f"Must be between {settings.FEMTOBOARD_MIN_POW_DIFFICULTY_BITS} and "
                    f"{settings.FEMTOBOARD_MAX_POW_DIFFICULTY_BITS} bits."
                )
        if errors:
            raise ValidationError(errors)

    def pow_difficulty_bits_for(self, action: str) -> int:
        """Server-enforced difficulty for an action type, clamped to the
        global floor/ceiling even if board configuration was corrupted or
        edited outside the admin interface (design doc 80.17)."""
        raw = {
            "THREAD": self.pow_difficulty_thread_bits,
            "REPLY": self.pow_difficulty_reply_bits,
            "REPORT": self.pow_difficulty_report_bits,
        }.get(action, settings.FEMTOBOARD_MAX_POW_DIFFICULTY_BITS)
        return max(
            settings.FEMTOBOARD_MIN_POW_DIFFICULTY_BITS,
            min(raw, settings.FEMTOBOARD_MAX_POW_DIFFICULTY_BITS),
        )

    def allowed_media_types(self) -> set[str]:
        allowed: set[str] = set()
        if self.allow_jpeg:
            allowed.add("image/jpeg")
        if self.allow_png:
            allowed.add("image/png")
        if self.allow_webp:
            allowed.add("image/webp")
        if self.allow_gif:
            allowed.add("image/gif")
        if self.allow_webm:
            allowed.add("video/webm")
        return allowed


class SiteConfiguration(models.Model):
    """Singleton row holding the global MOTD (design doc section 33)."""

    SINGLETON_ID: ClassVar[int] = 1

    id = models.PositiveIntegerField(primary_key=True, default=1, editable=False)
    global_motd = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site configuration"
        verbose_name_plural = "Site configuration"

    def __str__(self) -> str:
        return "Site configuration"

    def save(self, *args: object, **kwargs: object) -> None:
        self.id = self.SINGLETON_ID
        super().save(*args, **kwargs)  # type: ignore[arg-type]

    @classmethod
    def load(cls) -> SiteConfiguration:
        obj, _ = cls.objects.get_or_create(id=cls.SINGLETON_ID)
        return obj
