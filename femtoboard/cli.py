"""Console-script entry points used by the Nix package.

``femtoboard-manage`` is the ``manage.py`` equivalent; ``femtoboard-serve``
runs the production WSGI app under gunicorn, embedded via gunicorn's
application API so the NixOS module doesn't need to locate gunicorn's own
binary or juggle PYTHONPATH separately (this package's console-script
wrapper already carries the full dependency closure, gunicorn included).
"""

from __future__ import annotations

import os
import sys
from typing import Any


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "femtoboard.settings.prod")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


def serve() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "femtoboard.settings.prod")
    from gunicorn.app.base import BaseApplication

    bind = os.environ.get("FEMTOBOARD_BIND", "127.0.0.1:8731")
    workers = os.environ.get("FEMTOBOARD_WORKERS", "3")

    class WSGIApp(BaseApplication):  # type: ignore[misc]
        def load_config(self) -> None:
            self.cfg.set("bind", [bind])
            self.cfg.set("workers", int(workers))
            self.cfg.set("accesslog", "-")
            self.cfg.set("errorlog", "-")

        def load(self) -> Any:
            from femtoboard.wsgi import application

            return application

    WSGIApp().run()


if __name__ == "__main__":
    main()
