from __future__ import annotations

import os
from typing import Any

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "femtoboard.settings.prod")

application: Any = get_asgi_application()
