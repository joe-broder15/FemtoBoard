from __future__ import annotations

from django import template
from django.utils.html import format_html
from django.utils.safestring import SafeString

from posts.models import Post
from posts.rendering import render_post_body

register = template.Library()


@register.filter(name="render_body")
def render_body(post: Post) -> SafeString:
    if post.is_tombstone:
        return SafeString("")
    target_thread_ids = {
        ref.target_post_id: ref.target_post.thread_id
        for ref in post.references_made.select_related("target_post").all()
    }
    return render_post_body(
        post.body, board_code=post.board.code, target_thread_ids=target_thread_ids
    )


@register.filter(name="backlinks")
def backlinks(post: Post) -> SafeString:
    board_code = post.board.code
    links = []
    for ref in post.referenced_by.select_related("source_post").all():
        source = ref.source_post
        target_thread_ids = {source.id: source.thread_id}
        links.append(
            render_post_body(
                f">>{source.id}", board_code=board_code, target_thread_ids=target_thread_ids
            )
        )
    if not links:
        return SafeString("")
    return format_html("Replies: {}", format_html(" ".join(str(link) for link in links)))


@register.filter(name="post_dom_id")
def post_dom_id(post: Post) -> str:
    return f"p{post.id}"
