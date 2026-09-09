from __future__ import annotations

from django.conf import settings
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_POST

from antispam.ip import get_client_ip
from antispam.services import check_and_increment


@sensitive_post_parameters("password")
@csrf_protect
def staff_login(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("moderation:dashboard")

    if request.method == "POST":
        client_ip = get_client_ip(request)
        allowed = check_and_increment(
            "staff_login",
            client_ip,
            window_seconds=settings.FEMTOBOARD_STAFF_LOGIN_RATE_LIMIT_WINDOW_SECONDS,
            limit=settings.FEMTOBOARD_STAFF_LOGIN_RATE_LIMIT_COUNT,
        )
        if not allowed:
            form = AuthenticationForm(request)
            form.add_error(None, "Too many login attempts. Please wait and try again.")
            return render(request, "accounts/login.html", {"form": form}, status=429)

        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            next_url = request.POST.get("next", "")
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                return redirect(next_url)
            return redirect("moderation:dashboard")
    else:
        form = AuthenticationForm(request)

    return render(request, "accounts/login.html", {"form": form})


@require_POST
def staff_logout(request: HttpRequest) -> HttpResponse:
    auth_logout(request)
    return redirect("accounts:login")
