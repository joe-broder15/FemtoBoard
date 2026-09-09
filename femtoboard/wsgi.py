from __future__ import annotations

import os

from django.core.handlers.wsgi import WSGIHandler
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "femtoboard.settings.prod")

application: WSGIHandler = get_wsgi_application()
