from __future__ import annotations

from django.urls import path

from moderation import views

app_name = "moderation"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("reports/", views.report_list, name="report_list"),
    path("reports/<int:report_id>/", views.report_detail, name="report_detail"),
    path("reports/<int:report_id>/resolve/", views.report_resolve, name="report_resolve"),
    path("posts/<int:post_id>/delete/", views.post_delete, name="post_delete"),
    path("threads/<int:thread_id>/delete/", views.thread_delete, name="thread_delete"),
    path("threads/<int:thread_id>/lock/", views.thread_lock_toggle, name="thread_lock_toggle"),
    path(
        "threads/<int:thread_id>/sticky/",
        views.thread_sticky_toggle,
        name="thread_sticky_toggle",
    ),
    path("bans/", views.ban_list, name="ban_list"),
    path("bans/issue/", views.ban_issue, name="ban_issue"),
    path("bans/<int:ban_id>/revoke/", views.ban_revoke, name="ban_revoke"),
    path("ip-search/", views.ip_search, name="ip_search"),
]
