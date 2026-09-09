"""Catch-up hard-pruning sweep across all boards (design doc section 17).

Normally pruning happens inline whenever a new thread is created; this
command exists for cases like an administrator lowering a board's
maximum active threads, where existing boards need to catch up.
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from boards.models import Board
from posts.models import Thread
from posts.services import prune_board_if_over_limit


class Command(BaseCommand):
    help = "Hard-prune the oldest non-stickied threads on any board over its active-thread limit."

    def handle(self, *args: Any, **options: Any) -> None:
        for board in Board.objects.all():
            before = Thread.objects.filter(board=board).count()
            count = before
            while count > board.max_active_threads:
                prune_board_if_over_limit(board)
                new_count = Thread.objects.filter(board=board).count()
                if new_count == count:
                    break  # nothing left eligible to prune (e.g. all stickied)
                count = new_count
            after = Thread.objects.filter(board=board).count()
            if before != after:
                self.stdout.write(f"/{board.code}/: pruned {before - after} thread(s).")
        self.stdout.write(self.style.SUCCESS("Prune sweep complete."))
