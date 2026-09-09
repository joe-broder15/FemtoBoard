from __future__ import annotations

from django.urls import path

from boards import views

app_name = "boards"

urlpatterns = [
    path("", views.home, name="home"),
    path("<str:board_code>/catalog/", views.catalog, name="catalog"),
    path("<str:board_code>/<int:page>/", views.board_index, name="board_index_page"),
    path("<str:board_code>/", views.board_index, name="board_index"),
]
