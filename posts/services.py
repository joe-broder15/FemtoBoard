"""Core posting, deletion, and pruning business logic.

Views should not write directly to Thread/Post/PostMedia; they should
call these functions so invariants (bump/sage rules, tombstoning, media
limits, hard pruning) stay in one place.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.contrib.auth.hashers import check_password, make_password
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone

from antispam.services import check_and_increment
from boards.models import Board
from mediafiles.processing import delete_media_files, process_media_upload
from mediafiles.validation import MediaValidationError
from posts.models import Post, PostMedia, PostReference, Thread, TombstoneReason
from posts.rendering import extract_referenced_ids
from posts.tripcode import derive_tripcode, split_name_and_secret


class PostingError(Exception):
    """Raised for any request-fixable posting failure (shown to the user)."""


@dataclass(frozen=True)
class Identity:
    display_name: str
    tripcode: str


def resolve_identity(raw_name: str, *, tripcodes_enabled: bool) -> Identity:
    name, secret = split_name_and_secret(raw_name)
    name = name[:64]
    tripcode = ""
    if secret and tripcodes_enabled:
        tripcode = derive_tripcode(secret)
    return Identity(display_name=name, tripcode=tripcode)


def _attach_media(post: Post, uploaded_file: UploadedFile[Any], board: Board) -> None:
    try:
        processed = process_media_upload(
            uploaded_file,
            allowed_types=board.allowed_media_types(),
            max_image_bytes=board.max_image_bytes,
            max_webm_bytes=board.max_webm_bytes,
        )
    except MediaValidationError as exc:
        raise PostingError(str(exc)) from exc
    PostMedia.objects.create(
        post=post,
        media_type=processed.media_type,
        mime_type=processed.mime_type,
        file=processed.relative_path,
        thumbnail=processed.thumbnail_relative_path,
        original_filename=(uploaded_file.name or "upload")[:255],
        file_size_bytes=processed.file_size_bytes,
        width=processed.width,
        height=processed.height,
        duration_seconds=processed.duration_seconds,
    )


def _link_references(post: Post) -> None:
    ids = extract_referenced_ids(post.body)
    if not ids:
        return
    targets = Post.objects.filter(id__in=ids, thread__board_id=post.thread.board_id).exclude(
        id=post.id
    )
    PostReference.objects.bulk_create(
        [PostReference(source_post=post, target_post=t) for t in targets],
        ignore_conflicts=True,
    )


def prune_board_if_over_limit(board: Board) -> None:
    """Hard-prune the oldest non-stickied thread once the board exceeds
    its configured maximum active threads (design doc section 17)."""
    active_count = Thread.objects.filter(board=board).count()
    if active_count <= board.max_active_threads:
        return
    candidate = Thread.objects.filter(board=board, stickied=False).order_by("bumped_at").first()
    if candidate is None:
        return
    delete_thread_hard(candidate)


def delete_thread_hard(thread: Thread) -> None:
    """Permanently remove a thread: DB rows (post, media, references all
    cascade) and the underlying media/thumbnail files on disk."""
    media_paths = list(
        PostMedia.objects.filter(post__thread=thread).values_list("file", "thumbnail")
    )
    thread.delete()
    for file_path, thumb_path in media_paths:
        delete_media_files(
            relative_path=str(file_path or ""), thumbnail_relative_path=str(thumb_path or "")
        )


def tombstone_reply(post: Post, reason: str) -> Post:
    if post.is_opening_post:
        raise PostingError("Opening posts cannot be deleted individually.")
    if post.is_tombstone:
        return post
    media = PostMedia.objects.filter(post=post).first()
    if media is not None:
        delete_media_files(
            relative_path=str(media.file), thumbnail_relative_path=str(media.thumbnail)
        )
        media.delete()
    post.is_tombstone = True
    post.tombstone_reason = reason
    post.subject = ""
    post.body = ""
    post.display_name = ""
    post.tripcode = ""
    post.deletion_password_hash = ""
    post.save()
    return post


@transaction.atomic
def create_thread(
    *,
    board: Board,
    subject: str,
    body: str,
    raw_name: str,
    uploaded_file: UploadedFile[Any],
    client_ip: str,
) -> Thread:
    if not board.enabled or not board.new_threads_enabled:
        raise PostingError("New threads are currently disabled on this board.")
    identity = resolve_identity(raw_name, tripcodes_enabled=board.tripcodes_enabled)
    thread = Thread.objects.create(board=board)
    post = Post.objects.create(
        thread=thread,
        is_opening_post=True,
        subject=subject[:100],
        body=body[: board.max_post_length],
        display_name=identity.display_name,
        tripcode=identity.tripcode,
        ip_address=client_ip,
    )
    _attach_media(post, uploaded_file, board)
    _link_references(post)
    prune_board_if_over_limit(board)
    return thread


@transaction.atomic
def create_reply(
    *,
    thread: Thread,
    body: str,
    raw_name: str,
    uploaded_file: UploadedFile[Any] | None,
    deletion_password: str,
    sage: bool,
    client_ip: str,
) -> Post:
    board = thread.board
    if thread.locked:
        raise PostingError("This thread is locked.")
    if not body and uploaded_file is None:
        raise PostingError("A reply must contain text, media, or both.")
    if uploaded_file is not None and thread.media_count() >= board.max_media_per_thread:
        raise PostingError("This thread has reached its media limit.")

    identity = resolve_identity(raw_name, tripcodes_enabled=board.tripcodes_enabled)
    post = Post.objects.create(
        thread=thread,
        is_opening_post=False,
        body=body[: board.max_post_length],
        display_name=identity.display_name,
        tripcode=identity.tripcode,
        sage=sage,
        ip_address=client_ip,
        deletion_password_hash=make_password(deletion_password) if deletion_password else "",
    )
    if uploaded_file is not None:
        _attach_media(post, uploaded_file, board)
    _link_references(post)

    if not sage and not thread.is_over_bump_limit():
        thread.bumped_at = post.created_at
        thread.save(update_fields=["bumped_at"])
    return post


def verify_and_tombstone_by_password(*, post_id: int, password: str, client_ip: str) -> bool:
    """Verify a reply's deletion password and tombstone it if it matches.

    Always returns a plain bool, and takes the same code path whether the
    post does not exist, is an opening post, is already deleted, or has
    no deletion password set -- so a caller cannot use the response to
    probe for which of those is true (design doc 80.16).
    """
    try:
        post = Post.objects.select_related("thread__board").get(id=post_id)
    except Post.DoesNotExist:
        return False

    board = post.thread.board
    allowed = check_and_increment(
        "deletion_password",
        client_ip,
        window_seconds=board.deletion_password_window_seconds,
        limit=board.deletion_password_attempts_per_window,
    )
    if not allowed:
        return False
    if post.is_opening_post or post.is_tombstone or not post.deletion_password_hash:
        return False
    if not check_password(password, post.deletion_password_hash):
        return False

    tombstone_reply(post, TombstoneReason.USER)
    return True


def lock_thread(thread: Thread) -> None:
    thread.locked = True
    thread.save(update_fields=["locked"])


def unlock_thread(thread: Thread) -> None:
    thread.locked = False
    thread.save(update_fields=["locked"])


def sticky_thread(thread: Thread) -> None:
    thread.stickied = True
    thread.stickied_at = timezone.now()
    thread.save(update_fields=["stickied", "stickied_at"])


def unsticky_thread(thread: Thread) -> None:
    thread.stickied = False
    thread.save(update_fields=["stickied"])


__all__ = [
    "Identity",
    "PostingError",
    "create_reply",
    "create_thread",
    "delete_thread_hard",
    "lock_thread",
    "prune_board_if_over_limit",
    "resolve_identity",
    "sticky_thread",
    "tombstone_reply",
    "unlock_thread",
    "unsticky_thread",
    "verify_and_tombstone_by_password",
]
