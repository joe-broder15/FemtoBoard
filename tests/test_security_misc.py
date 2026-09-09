from __future__ import annotations

from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from boards.models import SiteConfiguration
from posts.models import Post, Thread
from posts.services import create_thread

from .conftest import make_test_image

pytestmark = pytest.mark.django_db


def test_get_cannot_delete_post(client: Client, admin_user, board) -> None:
    thread = Thread.objects.create(board=board)
    post = Post.objects.create(thread=thread, is_opening_post=False, body="x")
    client.force_login(admin_user)
    response = client.get(reverse("moderation:post_delete", args=[post.id]))
    assert response.status_code == 302
    post.refresh_from_db()
    assert not post.is_tombstone


def test_get_cannot_issue_ban(client: Client, admin_user) -> None:
    client.force_login(admin_user)
    response = client.get(reverse("moderation:ban_issue"))
    assert response.status_code == 200  # renders the form, does not create a ban
    from moderation.models import Ban

    assert Ban.objects.count() == 0


def test_get_cannot_lock_thread(client: Client, admin_user, board) -> None:
    thread = Thread.objects.create(board=board)
    client.force_login(admin_user)
    client.get(reverse("moderation:thread_lock_toggle", args=[thread.id]))
    thread.refresh_from_db()
    assert not thread.locked


def test_csrf_protection_enforced_on_deletion(board) -> None:
    csrf_client = Client(enforce_csrf_checks=True)
    thread = create_thread(
        board=board,
        subject="",
        body="op",
        raw_name="",
        uploaded_file=make_test_image(),
        client_ip="1.1.1.1",
    )
    reply = thread.posts.create(is_opening_post=False, body="x")
    from django.contrib.auth.hashers import make_password

    reply.deletion_password_hash = make_password("pw")
    reply.save()
    response = csrf_client.post("/delete/", {"post_id": reply.id, "deletion_password": "pw"})
    assert response.status_code == 403


def test_post_body_html_is_escaped(board) -> None:
    thread = create_thread(
        board=board,
        subject="<script>alert(1)</script>",
        body="<img src=x onerror=alert(1)>",
        raw_name="",
        uploaded_file=make_test_image(),
        client_ip="1.1.1.1",
    )
    client = Client()
    response = client.get(f"/{board.code}/thread/{thread.id}/")
    content = response.content.decode()
    assert "<script>alert(1)</script>" not in content
    assert "<img src=x onerror=alert(1)>" not in content
    assert "&lt;script&gt;" in content


def test_motd_html_is_escaped(client: Client, board) -> None:
    config = SiteConfiguration.load()
    config.global_motd = "<script>alert('motd')</script>"
    config.save()
    response = client.get("/")
    content = response.content.decode()
    assert "<script>alert" not in content
    assert "&lt;script&gt;" in content


def test_open_redirect_target_rejected(board) -> None:
    client = Client()
    thread = create_thread(
        board=board,
        subject="",
        body="op",
        raw_name="",
        uploaded_file=make_test_image(),
        client_ip="1.1.1.1",
    )
    reply = thread.posts.create(is_opening_post=False, body="x")
    from django.contrib.auth.hashers import make_password

    reply.deletion_password_hash = make_password("pw")
    reply.save()
    response = client.post(
        "/delete/",
        {"post_id": reply.id, "deletion_password": "pw"},
        HTTP_REFERER="https://evil.example/steal",
    )
    assert response.status_code == 302
    assert response.url.startswith("/")  # type: ignore[attr-defined]
    assert "evil.example" not in response.url  # type: ignore[attr-defined]


def test_ip_removed_after_retention_window(board) -> None:
    thread = create_thread(
        board=board,
        subject="",
        body="op",
        raw_name="",
        uploaded_file=make_test_image(),
        client_ip="203.0.113.50",
    )
    op = thread.posts.get(is_opening_post=True)
    assert op.ip_address == "203.0.113.50"

    from django.core.management import call_command

    op.created_at = timezone.now() - timedelta(days=31)
    Post.objects.filter(id=op.id).update(created_at=op.created_at)
    call_command("cleanup_expired_ips")
    op.refresh_from_db()
    assert op.ip_address is None
    assert op.ip_removed_at is not None


def test_ip_not_removed_before_retention_window(board) -> None:
    thread = create_thread(
        board=board,
        subject="",
        body="op",
        raw_name="",
        uploaded_file=make_test_image(),
        client_ip="203.0.113.51",
    )
    op = thread.posts.get(is_opening_post=True)
    from django.core.management import call_command

    call_command("cleanup_expired_ips")
    op.refresh_from_db()
    assert op.ip_address == "203.0.113.51"


def test_private_moderator_note_never_in_public_ban_notice(client: Client, board) -> None:
    from moderation.models import Ban

    Ban.objects.create(
        ip_address="127.0.0.1",
        board=board,
        public_reason="Public reason text",
        internal_note="SECRET INTERNAL NOTE",
    )
    response = client.get(f"/{board.code}/")
    content = response.content.decode()
    assert "Public reason text" in content
    assert "SECRET INTERNAL NOTE" not in content
