from __future__ import annotations

from datetime import timedelta

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from antispam.ip import get_client_ip
from antispam.services import check_and_increment, verify_and_consume_challenge
from boards.models import Board
from moderation.bans import get_active_ban
from moderation.models import Report, ReportStatus
from posts.forms import DeletionForm, ReplyForm, ReportForm, ThreadForm
from posts.models import Post, Thread
from posts.services import (
    PostingError,
    create_reply,
    create_thread,
    verify_and_tombstone_by_password,
)


def _error_page(
    request: HttpRequest, board: Board, message: str, status: int = 400
) -> HttpResponse:
    return render(
        request, "posts/posting_error.html", {"board": board, "message": message}, status=status
    )


def _banned_page(request: HttpRequest, board: Board, ban: object) -> HttpResponse:
    return render(request, "posts/banned.html", {"board": board, "ban": ban}, status=403)


def thread_detail(request: HttpRequest, board_code: str, thread_id: int) -> HttpResponse:
    board = get_object_or_404(Board, code=board_code, enabled=True)
    thread = get_object_or_404(Thread.objects.select_related("board"), id=thread_id, board=board)
    posts = list(
        thread.posts.select_related("media")
        .prefetch_related("references_made__target_post", "referenced_by__source_post")
        .order_by("id")
    )
    ban = get_active_ban(ip_address=get_client_ip(request), board_code=board.code)
    return render(
        request,
        "posts/thread_detail.html",
        {
            "board": board,
            "thread": thread,
            "posts": posts,
            "active_ban": ban,
            "reply_form": ReplyForm(board=board),
            "report_form": ReportForm(),
        },
    )


@require_POST
def thread_create(request: HttpRequest, board_code: str) -> HttpResponse:
    board = get_object_or_404(Board, code=board_code)
    client_ip = get_client_ip(request)

    ban = get_active_ban(ip_address=client_ip, board_code=board.code)
    if ban:
        return _banned_page(request, board, ban)

    if not board.enabled or not board.new_threads_enabled:
        return _error_page(request, board, "New threads are currently disabled on this board.")

    if not check_and_increment(
        "thread",
        client_ip,
        window_seconds=board.thread_rate_limit_window_seconds,
        limit=board.thread_rate_limit_count,
    ):
        return _error_page(request, board, "You are posting too quickly. Please wait.", status=429)

    pow_id = request.POST.get("pow_id", "")
    pow_nonce = request.POST.get("pow_nonce", "")
    if not verify_and_consume_challenge(
        challenge_id=pow_id, board=board, action="THREAD", nonce=pow_nonce
    ):
        return _error_page(request, board, "Invalid or expired proof-of-work. Please retry.")

    form = ThreadForm(request.POST, request.FILES, board=board)
    if not form.is_valid():
        return _error_page(
            request,
            board,
            " ".join(str(e) for e in form.non_field_errors()) or "Invalid submission.",
        )

    try:
        thread = create_thread(
            board=board,
            subject=form.cleaned_data["subject"],
            body=form.cleaned_data["body"],
            raw_name=form.cleaned_data["name"],
            uploaded_file=form.cleaned_data["media"],
            client_ip=client_ip,
        )
    except PostingError as exc:
        return _error_page(request, board, str(exc))

    return redirect("posts:thread_detail", board_code=board.code, thread_id=thread.id)


@require_POST
def reply_create(request: HttpRequest, board_code: str, thread_id: int) -> HttpResponse:
    board = get_object_or_404(Board, code=board_code)
    thread = get_object_or_404(Thread, id=thread_id, board=board)
    client_ip = get_client_ip(request)

    ban = get_active_ban(ip_address=client_ip, board_code=board.code)
    if ban:
        return _banned_page(request, board, ban)

    if not check_and_increment(
        "reply",
        client_ip,
        window_seconds=board.reply_rate_limit_window_seconds,
        limit=board.reply_rate_limit_count,
    ):
        return _error_page(request, board, "You are posting too quickly. Please wait.", status=429)

    pow_id = request.POST.get("pow_id", "")
    pow_nonce = request.POST.get("pow_nonce", "")
    if not verify_and_consume_challenge(
        challenge_id=pow_id, board=board, action="REPLY", nonce=pow_nonce
    ):
        return _error_page(request, board, "Invalid or expired proof-of-work. Please retry.")

    form = ReplyForm(request.POST, request.FILES, board=board)
    if not form.is_valid():
        return _error_page(
            request,
            board,
            " ".join(str(e) for e in form.non_field_errors()) or "Invalid submission.",
        )

    try:
        post = create_reply(
            thread=thread,
            body=form.cleaned_data["body"],
            raw_name=form.cleaned_data["name"],
            uploaded_file=form.cleaned_data.get("media") or None,
            deletion_password=form.cleaned_data["deletion_password"],
            sage=form.cleaned_data["sage"],
            client_ip=client_ip,
        )
    except PostingError as exc:
        return _error_page(request, board, str(exc))

    return redirect(reverse("posts:thread_detail", args=[board.code, thread.id]) + f"#p{post.id}")


@require_POST
def delete_by_password(request: HttpRequest) -> HttpResponse:
    form = DeletionForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Invalid deletion request.")
        return redirect("boards:home")

    client_ip = get_client_ip(request)
    success = verify_and_tombstone_by_password(
        post_id=form.cleaned_data["post_id"],
        password=form.cleaned_data["deletion_password"],
        client_ip=client_ip,
    )
    if success:
        messages.success(request, "Post deleted.")
    else:
        messages.error(request, "Incorrect password or post cannot be deleted.")

    referer = request.META.get("HTTP_REFERER", "")
    if referer and url_has_allowed_host_and_scheme(
        referer, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(referer)
    return redirect("boards:home")


@require_POST
def report_post(request: HttpRequest, board_code: str, post_id: int) -> HttpResponse:
    board = get_object_or_404(Board, code=board_code)
    post = get_object_or_404(Post.objects.select_related("thread"), id=post_id, thread__board=board)
    client_ip = get_client_ip(request)

    if not check_and_increment(
        "report",
        client_ip,
        window_seconds=board.report_rate_limit_window_seconds,
        limit=board.report_rate_limit_count,
    ):
        return _error_page(
            request, board, "You are reporting too quickly. Please wait.", status=429
        )

    if board.report_requires_pow:
        pow_id = request.POST.get("pow_id", "")
        pow_nonce = request.POST.get("pow_nonce", "")
        if not verify_and_consume_challenge(
            challenge_id=pow_id, board=board, action="REPORT", nonce=pow_nonce
        ):
            return _error_page(request, board, "Invalid or expired proof-of-work. Please retry.")

    form = ReportForm(request.POST)
    if not form.is_valid():
        return _error_page(request, board, "Invalid report submission.")

    dedupe_cutoff = timezone.now() - timedelta(seconds=board.report_duplicate_window_seconds)
    already_reported = Report.objects.filter(
        post=post, reporter_ip=client_ip, created_at__gte=dedupe_cutoff
    ).exists()
    if not already_reported:
        Report.objects.create(
            post=post,
            category=form.cleaned_data["category"],
            explanation=form.cleaned_data["explanation"],
            reporter_ip=client_ip,
            status=ReportStatus.OPEN,
        )

    messages.success(request, "Thank you, this post has been reported.")
    return redirect(
        reverse("posts:thread_detail", args=[board.code, post.thread_id]) + f"#p{post.id}"
    )
