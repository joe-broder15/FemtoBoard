from __future__ import annotations

from django.urls import path

from posts import views

app_name = "posts"

urlpatterns = [
    path("delete/", views.delete_by_password, name="delete_by_password"),
    path("<str:board_code>/thread/new/", views.thread_create, name="thread_create"),
    path("<str:board_code>/thread/<int:thread_id>/", views.thread_detail, name="thread_detail"),
    path(
        "<str:board_code>/thread/<int:thread_id>/reply/",
        views.reply_create,
        name="reply_create",
    ),
    path("<str:board_code>/post/<int:post_id>/report/", views.report_post, name="report_post"),
]
