from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from moderation.models import Ban, Report, ReportStatus
from posts.models import Post, Thread

pytestmark = pytest.mark.django_db


def _make_thread_with_post(board):
    thread = Thread.objects.create(board=board)
    post = Post.objects.create(thread=thread, is_opening_post=True, body="hello")
    return thread, post


def test_public_user_cannot_reach_staff_dashboard(client: Client) -> None:
    response = client.get(reverse("moderation:dashboard"))
    assert response.status_code == 302
    assert reverse("accounts:login") in response.url  # type: ignore[attr-defined]


def test_authenticated_non_staff_gets_403(client: Client, plain_user) -> None:
    client.force_login(plain_user)
    response = client.get(reverse("moderation:dashboard"))
    assert response.status_code == 403


def test_janitor_cannot_issue_permanent_ban(client: Client, janitor_user, board) -> None:
    client.force_login(janitor_user)
    response = client.post(
        reverse("moderation:ban_issue"),
        {
            "ip_address": "203.0.113.5",
            "board": board.id,
            "public_reason": "spam",
            "internal_note": "",
            "duration_hours": "",
        },
    )
    assert response.status_code == 403
    assert not Ban.objects.filter(ip_address="203.0.113.5").exists()


def test_admin_can_issue_permanent_ban(client: Client, admin_user, board) -> None:
    client.force_login(admin_user)
    response = client.post(
        reverse("moderation:ban_issue"),
        {
            "ip_address": "203.0.113.5",
            "board": board.id,
            "public_reason": "spam",
            "internal_note": "",
            "duration_hours": "",
        },
    )
    assert response.status_code == 302
    ban = Ban.objects.get(ip_address="203.0.113.5")
    assert ban.is_permanent()


def test_janitor_cannot_revoke_ban(client: Client, janitor_user, admin_user, board) -> None:
    ban = Ban.objects.create(
        ip_address="203.0.113.9", board=board, public_reason="x", issued_by=admin_user
    )
    client.force_login(janitor_user)
    response = client.post(reverse("moderation:ban_revoke", args=[ban.id]))
    assert response.status_code == 403
    ban.refresh_from_db()
    assert not ban.revoked


def test_janitor_has_no_unrestricted_ip_search(client: Client, janitor_user) -> None:
    client.force_login(janitor_user)
    response = client.get(reverse("moderation:ip_search"))
    assert response.status_code == 403


def test_admin_has_unrestricted_ip_search(client: Client, admin_user) -> None:
    client.force_login(admin_user)
    response = client.get(reverse("moderation:ip_search"))
    assert response.status_code == 200


def test_janitor_can_delete_post_and_lock_thread(client: Client, janitor_user, board) -> None:
    thread, post = _make_thread_with_post(board)
    reply = Post.objects.create(thread=thread, is_opening_post=False, body="reply")
    client.force_login(janitor_user)

    response = client.post(reverse("moderation:post_delete", args=[reply.id]))
    assert response.status_code == 302
    reply.refresh_from_db()
    assert reply.is_tombstone

    response = client.post(reverse("moderation:thread_lock_toggle", args=[thread.id]))
    assert response.status_code == 302
    thread.refresh_from_db()
    assert thread.locked


def test_janitor_cannot_configure_boards(client: Client, janitor_user, board) -> None:
    client.force_login(janitor_user)
    response = client.get(f"/staff/django-admin/boards/board/{board.id}/change/")
    assert response.status_code == 403


def test_plain_user_cannot_resolve_reports(client: Client, plain_user, board) -> None:
    thread, post = _make_thread_with_post(board)
    report = Report.objects.create(
        post=post, category="SPAM", reporter_ip="203.0.113.1", status=ReportStatus.OPEN
    )
    client.force_login(plain_user)
    response = client.post(
        reverse("moderation:report_resolve", args=[report.id]),
        {"action": "resolve", "internal_note": ""},
    )
    assert response.status_code == 403
    report.refresh_from_db()
    assert report.status == ReportStatus.OPEN
