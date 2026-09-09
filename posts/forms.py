from __future__ import annotations

from typing import Any

from django import forms
from django.core.files.uploadedfile import UploadedFile

from boards.models import Board

_NAME_MAX_LENGTH = 64
_DELETION_PASSWORD_MAX_LENGTH = 128


class ThreadForm(forms.Form):
    subject = forms.CharField(max_length=100, required=False)
    body = forms.CharField(required=False, widget=forms.Textarea)
    name = forms.CharField(max_length=_NAME_MAX_LENGTH, required=False)
    # "media" shadows Form.media (a django-stubs Media-typed property used
    # for widget CSS/JS asset bundling); this is a harmless naming clash at
    # runtime (cleaned_data["media"] works fine) but not to the type checker.
    media = forms.FileField(required=True)  # type: ignore[assignment]
    pow_id = forms.CharField(max_length=64)
    pow_nonce = forms.CharField(max_length=128)

    def __init__(self, *args: Any, board: Board, **kwargs: Any) -> None:
        self.board = board
        super().__init__(*args, **kwargs)

    def clean_body(self) -> str:
        body: str = self.cleaned_data.get("body", "")
        if len(body) > self.board.max_post_length:
            raise forms.ValidationError("Body is too long for this board.")
        return body

    def clean_media(self) -> UploadedFile[Any]:
        media: UploadedFile[Any] = self.cleaned_data["media"]
        return media


class ReplyForm(forms.Form):
    body = forms.CharField(required=False, widget=forms.Textarea)
    name = forms.CharField(max_length=_NAME_MAX_LENGTH, required=False)
    media = forms.FileField(required=False)  # type: ignore[assignment]
    deletion_password = forms.CharField(
        max_length=_DELETION_PASSWORD_MAX_LENGTH, required=False, widget=forms.PasswordInput
    )
    sage = forms.BooleanField(required=False)
    pow_id = forms.CharField(max_length=64)
    pow_nonce = forms.CharField(max_length=128)

    def __init__(self, *args: Any, board: Board, **kwargs: Any) -> None:
        self.board = board
        super().__init__(*args, **kwargs)

    def clean_body(self) -> str:
        body: str = self.cleaned_data.get("body", "")
        if len(body) > self.board.max_post_length:
            raise forms.ValidationError("Body is too long for this board.")
        return body

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        if not cleaned.get("body") and not cleaned.get("media"):
            raise forms.ValidationError("A reply must contain text, media, or both.")
        return cleaned


class DeletionForm(forms.Form):
    post_id = forms.IntegerField(min_value=1)
    deletion_password = forms.CharField(
        max_length=_DELETION_PASSWORD_MAX_LENGTH, widget=forms.PasswordInput
    )


class ReportForm(forms.Form):
    CATEGORY_CHOICES = (
        ("SPAM", "Spam"),
        ("ILLEGAL", "Illegal content"),
        ("RULE_VIOLATION", "Board rule violation"),
        ("HARASSMENT", "Harassment"),
        ("OTHER", "Other"),
    )

    category = forms.ChoiceField(choices=CATEGORY_CHOICES)
    explanation = forms.CharField(max_length=500, required=False, widget=forms.Textarea)
