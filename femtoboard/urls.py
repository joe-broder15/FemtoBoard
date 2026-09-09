from __future__ import annotations

from django.conf import settings
from django.contrib import admin
from django.urls import URLPattern, URLResolver, include, path

urlpatterns: list[URLPattern | URLResolver] = [
    path("staff/django-admin/", admin.site.urls),
    path("staff/", include("accounts.urls")),
    path("staff/", include("moderation.urls")),
    path("", include("antispam.urls")),
    # posts.urls must be tried before boards.urls: it contains a couple of
    # fixed top-level paths (e.g. "delete/") that would otherwise be
    # shadowed by boards.urls' catch-all "<board_code>/" pattern.
    path("", include("posts.urls")),
    path("", include("boards.urls")),
]

if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
