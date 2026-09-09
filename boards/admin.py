from __future__ import annotations

from typing import Any

from django.contrib import admin
from django.http import HttpRequest

from boards.models import Board, SiteConfiguration
from moderation.audit import record_action


@admin.register(Board)
class BoardAdmin(admin.ModelAdmin[Board]):
    list_display = ("code", "name", "enabled", "new_threads_enabled", "max_active_threads")
    search_fields = ("code", "name")

    def save_model(self, request: HttpRequest, obj: Board, form: Any, change: bool) -> None:
        super().save_model(request, obj, form, change)
        record_action(
            actor=request.user,
            verb="board.change" if change else "board.create",
            target=f"board:{obj.code}",
            reason="",
        )

    def delete_model(self, request: HttpRequest, obj: Board) -> None:
        code = obj.code
        super().delete_model(request, obj)
        record_action(actor=request.user, verb="board.delete", target=f"board:{code}", reason="")


@admin.register(SiteConfiguration)
class SiteConfigurationAdmin(admin.ModelAdmin[SiteConfiguration]):
    list_display = ("id", "updated_at")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return not SiteConfiguration.objects.exists()

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def save_model(
        self, request: HttpRequest, obj: SiteConfiguration, form: Any, change: bool
    ) -> None:
        super().save_model(request, obj, form, change)
        record_action(actor=request.user, verb="motd.global_change", target="site", reason="")
