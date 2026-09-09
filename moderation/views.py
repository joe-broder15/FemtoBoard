from __future__ import annotations

from datetime import timedelta
from typing import cast

from django.contrib import messages
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from moderation.audit import record_action
from moderation.forms import BanForm, ReportResolutionForm
from moderation.models import Ban, ModerationAction, Report, ReportStatus
from moderation.permissions import staff_required
from posts.models import Post, Thread, TombstoneReason
from posts.services import (
    delete_thread_hard,
    lock_thread,
    sticky_thread,
    tombstone_reply,
    unlock_thread,
    unsticky_thread,
)

_IP_CONTEXT_RECENT_POSTS = 5


@staff_required("moderation.view_report")
def dashboard(request: HttpRequest) -> HttpResponse:
    open_reports = Report.objects.filter(status=ReportStatus.OPEN).count()
    recent_actions: list[ModerationAction] = []
    if request.user.has_perm("moderation.view_ip_history"):
        recent_actions = list(ModerationAction.objects.select_related("actor")[:20])
    return render(
        request,
        "moderation/dashboard.html",
        {"open_reports": open_reports, "recent_actions": recent_actions},
    )


@staff_required("moderation.view_report")
def report_list(request: HttpRequest) -> HttpResponse:
    status = request.GET.get("status", ReportStatus.OPEN)
    valid_statuses = {choice[0] for choice in ReportStatus.choices}
    if status not in valid_statuses:
        status = ReportStatus.OPEN
    reports = (
        Report.objects.filter(status=status)
        .select_related("post__thread__board")
        .order_by("-created_at")[:200]
    )
    return render(request, "moderation/report_list.html", {"reports": reports, "status": status})


@staff_required("moderation.view_report")
def report_detail(request: HttpRequest, report_id: int) -> HttpResponse:
    report = get_object_or_404(Report.objects.select_related("post__thread__board"), id=report_id)
    post = report.post
    can_view_ip = request.user.has_perm("moderation.view_ip_history")
    ip_context = None
    if can_view_ip and post.ip_address:
        record_action(
            actor=request.user,
            verb="ip.contextual_view",
            target=f"post:{post.id}",
            reason=f"via report:{report.id}",
        )
        recent_posts = (
            Post.objects.filter(ip_address=post.ip_address)
            .exclude(id=post.id)
            .select_related("thread__board")
            .order_by("-created_at")[:_IP_CONTEXT_RECENT_POSTS]
        )
        active_bans = [
            b
            for b in Ban.objects.filter(ip_address=post.ip_address, revoked=False)
            if b.is_active()
        ]
        ip_context = {
            "ip_address": post.ip_address,
            "recent_posts": recent_posts,
            "active_bans": active_bans,
        }

    other_reports = Report.objects.filter(post=post).exclude(id=report.id).order_by("-created_at")

    return render(
        request,
        "moderation/report_detail.html",
        {
            "report": report,
            "post": post,
            "ip_context": ip_context,
            "other_reports": other_reports,
            "resolution_form": ReportResolutionForm(),
            "ban_form": BanForm(initial={"ip_address": post.ip_address} if can_view_ip else None),
        },
    )


@staff_required("moderation.resolve_report")
def report_resolve(request: HttpRequest, report_id: int) -> HttpResponse:
    if request.method != "POST":
        return redirect("moderation:report_detail", report_id=report_id)
    report = get_object_or_404(Report, id=report_id)
    form = ReportResolutionForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Invalid resolution submission.")
        return redirect("moderation:report_detail", report_id=report_id)

    action = form.cleaned_data["action"]
    report.status = ReportStatus.RESOLVED if action == "resolve" else ReportStatus.REJECTED
    report.internal_note = form.cleaned_data["internal_note"]
    report.resolved_by = cast(User, request.user)
    report.resolved_at = timezone.now()
    report.save()
    record_action(
        actor=request.user,
        verb=f"report.{report.status.lower()}",
        target=f"report:{report.id}",
        reason=form.cleaned_data["internal_note"],
    )
    messages.success(request, "Report updated.")
    return redirect("moderation:report_list")


@staff_required("posts.delete_post")
def post_delete(request: HttpRequest, post_id: int) -> HttpResponse:
    if request.method != "POST":
        return redirect("moderation:report_list")
    post = get_object_or_404(Post, id=post_id)
    if post.is_opening_post:
        messages.error(request, "Use thread deletion to remove an opening post.")
        return redirect("moderation:report_list")
    tombstone_reply(post, TombstoneReason.MODERATOR)
    record_action(
        actor=request.user,
        verb="post.delete",
        target=f"post:{post_id}",
        reason=request.POST.get("reason", ""),
    )
    messages.success(request, f"Post #{post_id} deleted.")
    return redirect(request.POST.get("next") or "moderation:report_list")


@staff_required("posts.delete_thread")
def thread_delete(request: HttpRequest, thread_id: int) -> HttpResponse:
    if request.method != "POST":
        return redirect("moderation:report_list")
    thread = get_object_or_404(Thread, id=thread_id)
    board_code = thread.board.code
    delete_thread_hard(thread)
    record_action(
        actor=request.user,
        verb="thread.delete",
        target=f"thread:{thread_id}",
        reason=request.POST.get("reason", ""),
    )
    messages.success(request, f"Thread #{thread_id} deleted.")
    return redirect("boards:board_index", board_code=board_code)


@staff_required("posts.lock_thread")
def thread_lock_toggle(request: HttpRequest, thread_id: int) -> HttpResponse:
    if request.method != "POST":
        return redirect("moderation:report_list")
    thread = get_object_or_404(Thread, id=thread_id)
    if thread.locked:
        unlock_thread(thread)
        verb = "thread.unlock"
    else:
        lock_thread(thread)
        verb = "thread.lock"
    record_action(actor=request.user, verb=verb, target=f"thread:{thread_id}", reason="")
    return redirect(request.POST.get("next") or "boards:board_index", board_code=thread.board.code)


@staff_required("posts.sticky_thread")
def thread_sticky_toggle(request: HttpRequest, thread_id: int) -> HttpResponse:
    if request.method != "POST":
        return redirect("moderation:report_list")
    thread = get_object_or_404(Thread, id=thread_id)
    if thread.stickied:
        unsticky_thread(thread)
        verb = "thread.unsticky"
    else:
        sticky_thread(thread)
        verb = "thread.sticky"
    record_action(actor=request.user, verb=verb, target=f"thread:{thread_id}", reason="")
    return redirect(request.POST.get("next") or "boards:board_index", board_code=thread.board.code)


@staff_required("moderation.add_ban")
def ban_issue(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        form = BanForm()
        return render(request, "moderation/ban_form.html", {"form": form})

    form = BanForm(request.POST)
    if not form.is_valid():
        return render(request, "moderation/ban_form.html", {"form": form}, status=400)

    duration_hours = form.cleaned_data["duration_hours"]
    if duration_hours is None and not request.user.has_perm("moderation.issue_permanent_ban"):
        messages.error(request, "You are not permitted to issue permanent bans.")
        return render(request, "moderation/ban_form.html", {"form": form}, status=403)

    expires_at = None
    if duration_hours is not None:
        expires_at = timezone.now() + timedelta(hours=duration_hours)

    ban = Ban.objects.create(
        ip_address=form.cleaned_data["ip_address"],
        board=form.cleaned_data["board"],
        public_reason=form.cleaned_data["public_reason"],
        internal_note=form.cleaned_data["internal_note"],
        issued_by=cast(User, request.user),
        expires_at=expires_at,
    )
    record_action(
        actor=request.user,
        verb="ban.create",
        target=f"ban:{ban.id}",
        reason=form.cleaned_data["public_reason"],
    )
    messages.success(request, "Ban issued.")
    return redirect("moderation:ban_list")


@staff_required("moderation.view_ban")
def ban_list(request: HttpRequest) -> HttpResponse:
    can_search = request.user.has_perm("moderation.search_ip")
    qs = Ban.objects.select_related("board", "issued_by").order_by("-created_at")
    ip_filter = request.GET.get("ip", "") if can_search else ""
    if ip_filter:
        qs = qs.filter(ip_address=ip_filter)
    return render(
        request,
        "moderation/ban_list.html",
        {"bans": qs[:200], "can_search": can_search, "ip_filter": ip_filter},
    )


@staff_required("moderation.change_ban")
def ban_revoke(request: HttpRequest, ban_id: int) -> HttpResponse:
    if request.method != "POST":
        return redirect("moderation:ban_list")
    ban = get_object_or_404(Ban, id=ban_id)
    ban.revoked = True
    ban.revoked_by = cast(User, request.user)
    ban.revoked_at = timezone.now()
    ban.save()
    record_action(actor=request.user, verb="ban.revoke", target=f"ban:{ban.id}", reason="")
    messages.success(request, "Ban revoked.")
    return redirect("moderation:ban_list")


@staff_required("moderation.search_ip")
def ip_search(request: HttpRequest) -> HttpResponse:
    ip = request.GET.get("ip", "").strip()
    if not ip:
        return render(request, "moderation/ip_search.html", {})
    record_action(actor=request.user, verb="ip.unrestricted_search", target=f"ip:{ip}", reason="")
    recent_posts = (
        Post.objects.filter(ip_address=ip)
        .select_related("thread__board")
        .order_by("-created_at")[:50]
    )
    active_bans = [b for b in Ban.objects.filter(ip_address=ip, revoked=False) if b.is_active()]
    return render(
        request,
        "moderation/ip_search.html",
        {"ip": ip, "recent_posts": recent_posts, "active_bans": active_bans},
    )
