from __future__ import annotations

from django.urls import path

from antispam import views

app_name = "antispam"

urlpatterns = [
    path("<str:board_code>/pow/<str:action>/", views.issue_challenge, name="issue_challenge"),
]
