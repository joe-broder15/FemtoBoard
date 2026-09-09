from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from antispam.ip import get_client_ip
from boards.models import Board
from moderation.bans import get_active_ban
from posts.models import Post, Thread

_CATALOG_SORT_MAP: dict[str, tuple[str, ...]] = {
    "bump": ("-stickied", "-bumped_at"),
    "new": ("-stickied", "-created_at"),
    "replies": ("-stickied", "-reply_count_annotated"),
}
_DEFAULT_SORT = "bump"


@dataclass
class ThreadPreview:
    thread: Thread
    opening_post: Post | None
    preview_replies: list[Post] = field(default_factory=list)


def _get_board(board_code: str) -> Board:
    return get_object_or_404(Board, code=board_code, enabled=True)


def _thread_ordering() -> list[str]:
    return ["-stickied", "-stickied_at", "-bumped_at"]


def _load_opening_posts(thread_ids: list[int]) -> dict[int, Post]:
    return {
        p.thread_id: p
        for p in Post.objects.filter(thread_id__in=thread_ids, is_opening_post=True).select_related(
            "media"
        )
    }


def _load_previews(thread_ids: list[int], preview_count: int) -> dict[int, list[Post]]:
    replies_by_thread: dict[int, list[Post]] = defaultdict(list)
    reply_qs = (
        Post.objects.filter(thread_id__in=thread_ids, is_opening_post=False)
        .select_related("media")
        .order_by("thread_id", "-id")
    )
    for post in reply_qs:
        bucket = replies_by_thread[post.thread_id]
        if len(bucket) < preview_count:
            bucket.append(post)
    for bucket in replies_by_thread.values():
        bucket.reverse()
    return replies_by_thread


def home(request: HttpRequest) -> HttpResponse:
    boards = Board.objects.filter(enabled=True).order_by("code")
    return render(request, "boards/home.html", {"boards": boards})


def board_index(request: HttpRequest, board_code: str, page: int = 1) -> HttpResponse:
    board = _get_board(board_code)
    qs = (
        Thread.objects.filter(board=board)
        .annotate(
            reply_count_annotated=Count("posts", filter=Q(posts__is_opening_post=False)),
            media_count_annotated=Count("posts__media"),
        )
        .order_by(*_thread_ordering())
    )
    paginator = Paginator(qs, board.threads_per_page)
    page_obj = paginator.get_page(page)
    threads = list(page_obj.object_list)
    thread_ids = [t.id for t in threads]
    ops = _load_opening_posts(thread_ids)
    previews = _load_previews(thread_ids, board.preview_reply_count)
    thread_previews = [
        ThreadPreview(thread=t, opening_post=ops.get(t.id), preview_replies=previews.get(t.id, []))
        for t in threads
    ]

    ban = get_active_ban(ip_address=get_client_ip(request), board_code=board.code)
    return render(
        request,
        "boards/board_index.html",
        {
            "board": board,
            "page_obj": page_obj,
            "thread_previews": thread_previews,
            "active_ban": ban,
        },
    )


def catalog(request: HttpRequest, board_code: str) -> HttpResponse:
    board = _get_board(board_code)
    sort = request.GET.get("sort", _DEFAULT_SORT)
    if sort not in _CATALOG_SORT_MAP:
        sort = _DEFAULT_SORT
    order_fields = _CATALOG_SORT_MAP[sort]

    qs = (
        Thread.objects.filter(board=board)
        .annotate(
            reply_count_annotated=Count("posts", filter=Q(posts__is_opening_post=False)),
            media_count_annotated=Count("posts__media"),
        )
        .order_by(*order_fields)
    )
    threads = list(qs)
    ops = _load_opening_posts([t.id for t in threads])
    cards = [ThreadPreview(thread=t, opening_post=ops.get(t.id)) for t in threads]

    return render(
        request,
        "boards/catalog.html",
        {"board": board, "cards": cards, "sort": sort},
    )
