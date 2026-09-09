"""Seed the initial boards (design doc section 1)."""

from __future__ import annotations

from django.db import migrations

_INITIAL_BOARDS = [
    {"code": "g", "name": "Technology", "description": "Technology discussion"},
    {"code": "b", "name": "Random", "description": "General discussion"},
    {"code": "meta", "name": "Meta", "description": "Discussion about Femtoboard"},
]


def seed_boards(apps, schema_editor):  # noqa: ANN001, ANN201
    Board = apps.get_model("boards", "Board")
    for data in _INITIAL_BOARDS:
        Board.objects.get_or_create(code=data["code"], defaults=data)


def remove_boards(apps, schema_editor):  # noqa: ANN001, ANN201
    Board = apps.get_model("boards", "Board")
    Board.objects.filter(code__in=[b["code"] for b in _INITIAL_BOARDS]).delete()


class Migration(migrations.Migration):
    dependencies = [("boards", "0001_initial")]

    operations = [migrations.RunPython(seed_boards, remove_boards)]
