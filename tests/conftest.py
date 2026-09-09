from __future__ import annotations

import hashlib
import io

import pytest
from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from boards.models import Board


def _leading_zero_bits(digest: bytes) -> int:
    bits = 0
    for byte in digest:
        if byte == 0:
            bits += 8
            continue
        bits += 8 - byte.bit_length()
        break
    return bits


def solve_pow(challenge: str, difficulty_bits: int) -> str:
    nonce = 0
    while True:
        digest = hashlib.sha256((challenge + str(nonce)).encode("utf-8")).digest()
        if _leading_zero_bits(digest) >= difficulty_bits:
            return str(nonce)
        nonce += 1


def make_test_image(color: tuple[int, int, int] = (10, 20, 30)) -> SimpleUploadedFile:
    buf = io.BytesIO()
    Image.new("RGB", (64, 48), color=color).save(buf, format="JPEG")
    buf.seek(0)
    return SimpleUploadedFile("test.jpg", buf.read(), content_type="image/jpeg")


@pytest.fixture
def board(db) -> Board:
    b, _ = Board.objects.get_or_create(
        code="t",
        defaults={
            "name": "Test board",
            "pow_difficulty_thread_bits": 12,
            "pow_difficulty_reply_bits": 12,
            "pow_difficulty_report_bits": 12,
        },
    )
    if b.pow_difficulty_thread_bits != 12:
        b.pow_difficulty_thread_bits = 12
        b.pow_difficulty_reply_bits = 12
        b.pow_difficulty_report_bits = 12
        b.save()
    return b


@pytest.fixture
def other_board(db) -> Board:
    b, _ = Board.objects.get_or_create(
        code="u",
        defaults={
            "name": "Other test board",
            "pow_difficulty_thread_bits": 12,
            "pow_difficulty_reply_bits": 12,
            "pow_difficulty_report_bits": 12,
        },
    )
    return b


@pytest.fixture
def admin_user(db) -> User:
    user = User.objects.create_user("admin_staff", password="pw12345!strong")  # noqa: S106
    user.is_staff = True
    user.save()
    user.groups.add(Group.objects.get(name="Administrators"))
    return user


@pytest.fixture
def janitor_user(db) -> User:
    user = User.objects.create_user("janitor_staff", password="pw12345!strong")  # noqa: S106
    user.is_staff = True
    user.save()
    user.groups.add(Group.objects.get(name="Janitors"))
    return user


@pytest.fixture
def plain_user(db) -> User:
    return User.objects.create_user("plain", password="pw12345!strong")  # noqa: S106


def pow_fields(board: Board, action: str) -> dict[str, str]:
    from antispam.services import issue_challenge

    issued = issue_challenge(
        board=board,
        action=action,
        client_ip="127.0.0.1",
        difficulty_bits=board.pow_difficulty_bits_for(action),
        ttl_seconds=board.pow_challenge_ttl_seconds,
    )
    nonce = solve_pow(issued.challenge, issued.difficulty_bits)
    return {"pow_id": issued.id, "pow_nonce": nonce}
