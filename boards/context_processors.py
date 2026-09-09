from __future__ import annotations

from typing import Any

from django.http import HttpRequest

from boards.models import Board, SiteConfiguration


def motd(request: HttpRequest) -> dict[str, Any]:
    return {
        "global_motd": SiteConfiguration.load().global_motd,
        "nav_boards": Board.objects.filter(enabled=True).order_by("code"),
    }
