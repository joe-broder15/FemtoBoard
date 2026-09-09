"""Ban lookups used by the posting pipeline (design doc section 48)."""

from __future__ import annotations

from django.db.models import Q
from django.utils import timezone

from moderation.models import Ban


def get_active_ban(*, ip_address: str, board_code: str) -> Ban | None:
    """Return the most relevant active ban for this IP/board, or None.

    Board-scoped bans only ever affect their own board; site-wide bans
    (``board`` is null) affect every board. A board-specific endpoint can
    never be used to dodge a site-wide ban, and a ban on one board can
    never leak onto another (design doc 80.21).
    """
    now = timezone.now()
    candidates = Ban.objects.filter(ip_address=ip_address, revoked=False).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now)
    )
    for ban in candidates:
        if ban.applies_to_board(board_code):
            return ban
    return None
