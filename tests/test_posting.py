from __future__ import annotations

import pytest

from posts.models import PostReference, Thread, TombstoneReason
from posts.services import (
    PostingError,
    create_reply,
    create_thread,
    delete_thread_hard,
    tombstone_reply,
    verify_and_tombstone_by_password,
)

from .conftest import make_test_image, pow_fields

pytestmark = pytest.mark.django_db


def test_opening_post_requires_media_at_view_level(client, board) -> None:
    response = client.post(
        f"/{board.code}/thread/new/",
        {"subject": "s", "body": "no media here", **pow_fields(board, "THREAD")},
    )
    # Django's FileField(required=True) rejects a submission with no file.
    assert response.status_code == 400


def test_reply_requires_text_or_media(board) -> None:
    thread = create_thread(
        board=board,
        subject="",
        body="op",
        raw_name="",
        uploaded_file=make_test_image(),
        client_ip="1.1.1.1",
    )
    with pytest.raises(PostingError):
        create_reply(
            thread=thread,
            body="",
            raw_name="",
            uploaded_file=None,
            deletion_password="",
            sage=False,
            client_ip="1.1.1.1",
        )


def test_opening_post_cannot_be_deleted_by_password(board) -> None:
    thread = create_thread(
        board=board,
        subject="",
        body="op",
        raw_name="",
        uploaded_file=make_test_image(),
        client_ip="1.1.1.1",
    )
    op = thread.posts.get(is_opening_post=True)
    op.deletion_password_hash = "irrelevant"
    op.save()
    success = verify_and_tombstone_by_password(
        post_id=op.id, password="anything", client_ip="9.9.9.9"
    )
    assert success is False
    op.refresh_from_db()
    assert not op.is_tombstone


def test_reply_tombstone_by_user_vs_moderator(board) -> None:
    thread = create_thread(
        board=board,
        subject="",
        body="op",
        raw_name="",
        uploaded_file=make_test_image(),
        client_ip="1.1.1.1",
    )
    reply = create_reply(
        thread=thread,
        body="hello",
        raw_name="",
        uploaded_file=None,
        deletion_password="secretpw",
        sage=False,
        client_ip="1.1.1.1",
    )
    ok = verify_and_tombstone_by_password(
        post_id=reply.id, password="secretpw", client_ip="2.2.2.2"
    )
    assert ok
    reply.refresh_from_db()
    assert reply.is_tombstone
    assert reply.tombstone_reason == TombstoneReason.USER
    assert reply.body == ""

    reply2 = create_reply(
        thread=thread,
        body="hello2",
        raw_name="",
        uploaded_file=None,
        deletion_password="",
        sage=False,
        client_ip="1.1.1.1",
    )
    tombstone_reply(reply2, TombstoneReason.MODERATOR)
    reply2.refresh_from_db()
    assert reply2.tombstone_reason == TombstoneReason.MODERATOR


def test_sage_does_not_bump(board) -> None:
    thread = create_thread(
        board=board,
        subject="",
        body="op",
        raw_name="",
        uploaded_file=make_test_image(),
        client_ip="1.1.1.1",
    )
    original_bump = thread.bumped_at
    create_reply(
        thread=thread,
        body="saged",
        raw_name="",
        uploaded_file=None,
        deletion_password="",
        sage=True,
        client_ip="1.1.1.1",
    )
    thread.refresh_from_db()
    assert thread.bumped_at == original_bump


def test_normal_reply_bumps(board) -> None:
    thread = create_thread(
        board=board,
        subject="",
        body="op",
        raw_name="",
        uploaded_file=make_test_image(),
        client_ip="1.1.1.1",
    )
    original_bump = thread.bumped_at
    create_reply(
        thread=thread,
        body="bump",
        raw_name="",
        uploaded_file=None,
        deletion_password="",
        sage=False,
        client_ip="1.1.1.1",
    )
    thread.refresh_from_db()
    assert thread.bumped_at > original_bump


def test_bump_limit_stops_further_bumping(board) -> None:
    board.bump_limit = 1
    board.save()
    thread = create_thread(
        board=board,
        subject="",
        body="op",
        raw_name="",
        uploaded_file=make_test_image(),
        client_ip="1.1.1.1",
    )
    create_reply(
        thread=thread,
        body="r1",
        raw_name="",
        uploaded_file=None,
        deletion_password="",
        sage=False,
        client_ip="1.1.1.1",
    )
    bumped_after_first = Thread.objects.get(id=thread.id).bumped_at
    create_reply(
        thread=thread,
        body="r2",
        raw_name="",
        uploaded_file=None,
        deletion_password="",
        sage=False,
        client_ip="1.1.1.1",
    )
    thread.refresh_from_db()
    assert thread.bumped_at == bumped_after_first


def test_locked_thread_rejects_replies(board) -> None:
    thread = create_thread(
        board=board,
        subject="",
        body="op",
        raw_name="",
        uploaded_file=make_test_image(),
        client_ip="1.1.1.1",
    )
    thread.locked = True
    thread.save()
    with pytest.raises(PostingError):
        create_reply(
            thread=thread,
            body="x",
            raw_name="",
            uploaded_file=None,
            deletion_password="",
            sage=False,
            client_ip="1.1.1.1",
        )


def test_same_board_reference_resolves_and_backlinks(board) -> None:
    thread = create_thread(
        board=board,
        subject="",
        body="op",
        raw_name="",
        uploaded_file=make_test_image(),
        client_ip="1.1.1.1",
    )
    op = thread.posts.get(is_opening_post=True)
    reply = create_reply(
        thread=thread,
        body=f">>{op.id} nice",
        raw_name="",
        uploaded_file=None,
        deletion_password="",
        sage=False,
        client_ip="1.1.1.1",
    )
    assert PostReference.objects.filter(source_post=reply, target_post=op).exists()


def test_cross_board_reference_does_not_resolve(board, other_board) -> None:
    thread_a = create_thread(
        board=board,
        subject="",
        body="op-a",
        raw_name="",
        uploaded_file=make_test_image(),
        client_ip="1.1.1.1",
    )
    op_a = thread_a.posts.get(is_opening_post=True)
    thread_b = create_thread(
        board=other_board,
        subject="",
        body=f">>{op_a.id} referencing another board",
        raw_name="",
        uploaded_file=make_test_image(),
        client_ip="1.1.1.1",
    )
    op_b = thread_b.posts.get(is_opening_post=True)
    assert not PostReference.objects.filter(source_post=op_b).exists()


def test_reference_to_nonexistent_post_is_not_linked(board) -> None:
    thread = create_thread(
        board=board,
        subject="",
        body=">>999999 nope",
        raw_name="",
        uploaded_file=make_test_image(),
        client_ip="1.1.1.1",
    )
    op = thread.posts.get(is_opening_post=True)
    assert not PostReference.objects.filter(source_post=op).exists()


def test_reference_to_pruned_thread_is_removed(board) -> None:
    thread = create_thread(
        board=board,
        subject="",
        body="op",
        raw_name="",
        uploaded_file=make_test_image(),
        client_ip="1.1.1.1",
    )
    op = thread.posts.get(is_opening_post=True)
    thread2 = create_thread(
        board=board,
        subject="",
        body=f">>{op.id}",
        raw_name="",
        uploaded_file=make_test_image(),
        client_ip="1.1.1.1",
    )
    op2 = thread2.posts.get(is_opening_post=True)
    assert PostReference.objects.filter(source_post=op2, target_post=op).exists()
    delete_thread_hard(thread)
    assert not PostReference.objects.filter(target_post_id=op.id).exists()


def test_hard_prune_removes_media_files(board) -> None:
    thread = create_thread(
        board=board,
        subject="",
        body="op",
        raw_name="",
        uploaded_file=make_test_image(),
        client_ip="1.1.1.1",
    )
    media = thread.posts.get(is_opening_post=True).media
    from django.core.files.storage import default_storage

    file_name = str(media.file.name)
    assert default_storage.exists(file_name)
    delete_thread_hard(thread)
    assert not default_storage.exists(file_name)
    assert not Thread.objects.filter(id=thread.id).exists()
