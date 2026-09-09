"""Rate limiting and proof-of-work service functions.

These are the only entry points the rest of the application should use
for abuse control; views must not implement ad-hoc counting.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.conf import settings
from django.db import DatabaseError, transaction
from django.db.models import F
from django.utils import timezone

from antispam.models import ActionType, ProofOfWorkChallenge, RateLimitCounter
from boards.models import Board

logger = logging.getLogger(__name__)


def _window_start(now: datetime, window_seconds: int) -> datetime:
    epoch = int(now.timestamp())
    aligned = epoch - (epoch % window_seconds)
    return datetime.fromtimestamp(aligned, tz=now.tzinfo)


def check_and_increment(scope: str, key: str, *, window_seconds: int, limit: int) -> bool:
    """Atomically record one event for (scope, key) and report if it is
    still within ``limit`` for the current fixed window.

    Fails closed: any database error is treated as "not allowed" rather
    than silently disabling the rate limit (design doc 80.18).
    """
    if limit <= 0:
        return False

    now = timezone.now()
    window_start = _window_start(now, window_seconds)

    try:
        with transaction.atomic():
            updated = RateLimitCounter.objects.filter(
                scope=scope, key=key, window_start=window_start
            ).update(count=F("count") + 1)
            if not updated:
                _obj, created = RateLimitCounter.objects.get_or_create(
                    scope=scope,
                    key=key,
                    window_start=window_start,
                    defaults={"count": 1},
                )
                if not created:
                    # Lost the race to create the window row; our event
                    # still needs to be counted against it.
                    RateLimitCounter.objects.filter(pk=_obj.pk).update(count=F("count") + 1)
            counter = RateLimitCounter.objects.get(scope=scope, key=key, window_start=window_start)
            return counter.count <= limit
    except DatabaseError:
        logger.exception("rate limit check failed for scope=%s key=%s", scope, key)
        return False


def cleanup_expired_rate_limits(*, older_than_hours: int = 24) -> int:
    cutoff = timezone.now() - timedelta(hours=older_than_hours)
    deleted, _ = RateLimitCounter.objects.filter(window_start__lt=cutoff).delete()
    return deleted


# --- Proof of work -----------------------------------------------------

_HEX_CHARS_PER_BYTE = 2


def _leading_zero_bits(digest: bytes) -> int:
    bits = 0
    for byte in digest:
        if byte == 0:
            bits += 8
            continue
        bits += 8 - byte.bit_length()
        break
    return bits


@dataclass(frozen=True)
class IssuedChallenge:
    id: str
    challenge: str
    difficulty_bits: int
    expires_at: datetime


def issue_challenge(
    *, board: Board, action: str, client_ip: str, difficulty_bits: int, ttl_seconds: int
) -> IssuedChallenge:
    difficulty_bits = max(
        settings.FEMTOBOARD_MIN_POW_DIFFICULTY_BITS,
        min(difficulty_bits, settings.FEMTOBOARD_MAX_POW_DIFFICULTY_BITS),
    )
    now = timezone.now()
    record = ProofOfWorkChallenge.objects.create(
        board=board,
        action=action,
        challenge=secrets.token_hex(32),
        difficulty_bits=difficulty_bits,
        client_ip=client_ip,
        expires_at=now + timedelta(seconds=ttl_seconds),
    )
    return IssuedChallenge(
        id=str(record.id),
        challenge=record.challenge,
        difficulty_bits=record.difficulty_bits,
        expires_at=record.expires_at,
    )


def verify_and_consume_challenge(
    *, challenge_id: str, board: Board, action: str, nonce: str
) -> bool:
    """Validate and atomically consume a proof-of-work solution.

    Returns True only if the challenge existed, matched the requested
    board/action, had not expired, had not already been consumed, and the
    supplied nonce satisfies the recorded difficulty. Consumption is a
    single conditional UPDATE so concurrent replay attempts cannot both
    succeed (design doc 80.17, 80.36).
    """
    try:
        record = ProofOfWorkChallenge.objects.get(id=challenge_id)
    except (ProofOfWorkChallenge.DoesNotExist, ValueError, DatabaseError):
        return False

    if record.board_id != board.id or record.action != action:
        return False
    if record.consumed_at is not None:
        return False
    if record.expires_at <= timezone.now():
        return False
    if len(nonce) > 128:
        return False

    digest = hashlib.sha256((record.challenge + nonce).encode("utf-8")).digest()
    if _leading_zero_bits(digest) < record.difficulty_bits:
        return False

    updated = ProofOfWorkChallenge.objects.filter(id=record.id, consumed_at__isnull=True).update(
        consumed_at=timezone.now()
    )
    return updated == 1


def cleanup_expired_challenges(*, older_than_hours: int = 24) -> int:
    cutoff = timezone.now() - timedelta(hours=older_than_hours)
    deleted, _ = ProofOfWorkChallenge.objects.filter(expires_at__lt=cutoff).delete()
    return deleted


__all__ = [
    "ActionType",
    "IssuedChallenge",
    "check_and_increment",
    "cleanup_expired_challenges",
    "cleanup_expired_rate_limits",
    "issue_challenge",
    "verify_and_consume_challenge",
]
