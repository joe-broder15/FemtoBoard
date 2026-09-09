from __future__ import annotations

from django.contrib import admin
from django.http import HttpRequest

from posts.models import Post, PostMedia, PostReference, Thread


class PostInline(admin.TabularInline[Post, Thread]):
    model = Post
    extra = 0
    fields = ("id", "is_opening_post", "is_tombstone", "created_at")
    readonly_fields = fields
    can_delete = False
    show_change_link = True


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin[Thread]):
    list_display = ("id", "board", "locked", "stickied", "bumped_at", "created_at")
    list_filter = ("board", "locked", "stickied")
    inlines = [PostInline]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False


@admin.register(Post)
class PostAdmin(admin.ModelAdmin[Post]):
    list_display = ("id", "thread", "is_opening_post", "is_tombstone", "created_at")
    list_filter = ("is_opening_post", "is_tombstone")
    search_fields = ("id",)
    readonly_fields = [f.name for f in Post._meta.fields]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Post | None = None) -> bool:
        return False


admin.site.register(PostMedia)
admin.site.register(PostReference)
