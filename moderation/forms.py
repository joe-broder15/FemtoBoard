from __future__ import annotations

from typing import Any

from django import forms

from boards.models import Board


class BanForm(forms.Form):
    ip_address = forms.GenericIPAddressField()
    board = forms.ModelChoiceField(
        queryset=Board.objects.all(), required=False, empty_label="Site-wide"
    )
    public_reason = forms.CharField(max_length=256)
    internal_note = forms.CharField(max_length=2000, required=False, widget=forms.Textarea)
    duration_hours = forms.IntegerField(
        required=False, min_value=1, max_value=8760, help_text="Leave blank for a permanent ban."
    )


class ReportResolutionForm(forms.Form):
    ACTION_CHOICES = (
        ("resolve", "Resolve"),
        ("reject", "Reject"),
    )

    action = forms.ChoiceField(choices=ACTION_CHOICES)
    internal_note = forms.CharField(max_length=2000, required=False, widget=forms.Textarea)

    def clean(self) -> dict[str, Any]:
        return super().clean() or {}
