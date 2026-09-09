from __future__ import annotations

from django.contrib import admin
from django.http import HttpRequest

from moderation.models import ModerationAction


@admin.register(ModerationAction)
class ModerationActionAdmin(admin.ModelAdmin[ModerationAction]):
    """Read-only audit trail. Never editable or deletable through any
    ordinary staff interface, including Django admin (design doc 80.22)."""

    list_display = ("created_at", "actor", "verb", "target")
    list_filter = ("verb",)
    search_fields = ("target", "reason")
    readonly_fields = [f.name for f in ModerationAction._meta.fields]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: ModerationAction | None = None
    ) -> bool:
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: ModerationAction | None = None
    ) -> bool:
        return False
