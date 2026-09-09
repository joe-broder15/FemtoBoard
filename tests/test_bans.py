from __future__ import annotations

import pytest

from moderation.bans import get_active_ban
from moderation.models import Ban

pytestmark = pytest.mark.django_db


def test_board_scoped_ban_does_not_affect_other_boards(board, other_board) -> None:
    Ban.objects.create(ip_address="198.51.100.1", board=board, public_reason="spam")
    assert get_active_ban(ip_address="198.51.100.1", board_code=board.code) is not None
    assert get_active_ban(ip_address="198.51.100.1", board_code=other_board.code) is None


def test_site_wide_ban_affects_every_board(board, other_board) -> None:
    Ban.objects.create(ip_address="198.51.100.2", board=None, public_reason="spam")
    assert get_active_ban(ip_address="198.51.100.2", board_code=board.code) is not None
    assert get_active_ban(ip_address="198.51.100.2", board_code=other_board.code) is not None


def test_revoked_ban_is_not_active(board) -> None:
    Ban.objects.create(ip_address="198.51.100.3", board=board, public_reason="spam", revoked=True)
    assert get_active_ban(ip_address="198.51.100.3", board_code=board.code) is None


def test_expired_temporary_ban_is_not_active(board) -> None:
    from datetime import timedelta

    from django.utils import timezone

    Ban.objects.create(
        ip_address="198.51.100.4",
        board=board,
        public_reason="spam",
        expires_at=timezone.now() - timedelta(hours=1),
    )
    assert get_active_ban(ip_address="198.51.100.4", board_code=board.code) is None


def test_banned_visitor_cannot_create_thread(client, board) -> None:
    from .conftest import make_test_image, pow_fields

    Ban.objects.create(ip_address="127.0.0.1", board=board, public_reason="spam")
    response = client.post(
        f"/{board.code}/thread/new/",
        {
            "subject": "s",
            "body": "hi",
            "media": make_test_image(),
            **pow_fields(board, "THREAD"),
        },
    )
    assert response.status_code == 403
    from posts.models import Thread

    assert not Thread.objects.filter(board=board).exists()
