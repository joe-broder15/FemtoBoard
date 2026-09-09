from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from antispam.services import (
    check_and_increment,
    issue_challenge,
    verify_and_consume_challenge,
)

from .conftest import solve_pow

pytestmark = pytest.mark.django_db


def test_pow_challenge_cannot_be_reused(board) -> None:
    issued = issue_challenge(
        board=board, action="THREAD", client_ip="1.1.1.1", difficulty_bits=12, ttl_seconds=600
    )
    nonce = solve_pow(issued.challenge, issued.difficulty_bits)
    assert verify_and_consume_challenge(
        challenge_id=issued.id, board=board, action="THREAD", nonce=nonce
    )
    assert not verify_and_consume_challenge(
        challenge_id=issued.id, board=board, action="THREAD", nonce=nonce
    )


def test_pow_challenge_cannot_cross_boards(board, other_board) -> None:
    issued = issue_challenge(
        board=board, action="THREAD", client_ip="1.1.1.1", difficulty_bits=12, ttl_seconds=600
    )
    nonce = solve_pow(issued.challenge, issued.difficulty_bits)
    assert not verify_and_consume_challenge(
        challenge_id=issued.id, board=other_board, action="THREAD", nonce=nonce
    )


def test_pow_challenge_cannot_cross_actions(board) -> None:
    issued = issue_challenge(
        board=board, action="THREAD", client_ip="1.1.1.1", difficulty_bits=12, ttl_seconds=600
    )
    nonce = solve_pow(issued.challenge, issued.difficulty_bits)
    assert not verify_and_consume_challenge(
        challenge_id=issued.id, board=board, action="REPLY", nonce=nonce
    )


def test_expired_pow_challenge_fails(board) -> None:
    from antispam.models import ProofOfWorkChallenge

    issued = issue_challenge(
        board=board, action="THREAD", client_ip="1.1.1.1", difficulty_bits=12, ttl_seconds=600
    )
    nonce = solve_pow(issued.challenge, issued.difficulty_bits)
    ProofOfWorkChallenge.objects.filter(id=issued.id).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    assert not verify_and_consume_challenge(
        challenge_id=issued.id, board=board, action="THREAD", nonce=nonce
    )


def test_wrong_nonce_fails(board) -> None:
    issued = issue_challenge(
        board=board, action="THREAD", client_ip="1.1.1.1", difficulty_bits=16, ttl_seconds=600
    )
    assert not verify_and_consume_challenge(
        challenge_id=issued.id, board=board, action="THREAD", nonce="0"
    )


def test_pow_difficulty_is_clamped_to_global_floor(board) -> None:
    issued = issue_challenge(
        board=board, action="THREAD", client_ip="1.1.1.1", difficulty_bits=0, ttl_seconds=600
    )
    assert issued.difficulty_bits >= 12  # FEMTOBOARD_MIN_POW_DIFFICULTY_BITS


def test_rate_limit_blocks_after_threshold() -> None:
    for _ in range(3):
        assert check_and_increment("test-scope", "1.2.3.4", window_seconds=60, limit=3)
    assert not check_and_increment("test-scope", "1.2.3.4", window_seconds=60, limit=3)


def test_rate_limit_is_per_key() -> None:
    for _ in range(3):
        assert check_and_increment("test-scope-2", "1.2.3.4", window_seconds=60, limit=3)
    assert check_and_increment("test-scope-2", "5.6.7.8", window_seconds=60, limit=3)
