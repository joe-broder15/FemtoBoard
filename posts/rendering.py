"""Safe rendering of post bodies with same-board >>NNN references.

Untrusted content is escaped first; only afterwards are server-controlled
anchor tags spliced in around digit sequences that were already resolved
to a real same-board post at *posting* time (via PostReference rows), so
no untrusted string is ever concatenated into a marked-safe fragment
(design doc 80.6, 22).
"""

from __future__ import annotations

import re

from django.urls import reverse
from django.utils.html import escape, format_html
from django.utils.safestring import SafeString, mark_safe

_ESCAPED_REF_PATTERN = re.compile(r"&gt;&gt;(\d+)")
_RAW_REF_PATTERN = re.compile(r">>(\d+)")


def extract_referenced_ids(raw_body: str) -> set[int]:
    return {int(m.group(1)) for m in _RAW_REF_PATTERN.finditer(raw_body)}


def render_post_body(
    raw_body: str, *, board_code: str, target_thread_ids: dict[int, int]
) -> SafeString:
    escaped = escape(raw_body)

    def _replace(match: re.Match[str]) -> str:
        post_id = int(match.group(1))
        thread_id = target_thread_ids.get(post_id)
        if thread_id is None:
            return match.group(0)
        url = reverse("posts:thread_detail", args=[board_code, thread_id]) + f"#p{post_id}"
        return format_html('<a class="post-ref" href="{}">&gt;&gt;{}</a>', url, post_id)

    linked = _ESCAPED_REF_PATTERN.sub(_replace, escaped)
    return mark_safe(linked.replace("\n", "<br>"))
