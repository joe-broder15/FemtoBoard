"""Permission decorators for staff views (design doc 80.3, 80.4).

Every privileged view must go through one of these: unauthenticated
visitors are redirected to login, authenticated staff lacking the
required permission get a 403. UI visibility is never treated as
authorization.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps

from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpRequest, HttpResponse

_View = Callable[..., HttpResponse]


def staff_required(*perms: str) -> Callable[[_View], _View]:
    def decorator(view_func: _View) -> _View:
        wrapped = permission_required(perms, raise_exception=True)(view_func)
        wrapped = login_required(login_url="accounts:login")(wrapped)

        @wraps(view_func)
        def entrypoint(request: HttpRequest, *args: object, **kwargs: object) -> HttpResponse:
            # Baseline gate regardless of which perms were requested: only
            # staff (Administrators/Janitors) accounts may reach any view
            # behind this decorator, even one called with no perms.
            if request.user.is_authenticated and not request.user.is_staff:
                from django.core.exceptions import PermissionDenied

                raise PermissionDenied
            return wrapped(request, *args, **kwargs)

        return entrypoint

    return decorator
