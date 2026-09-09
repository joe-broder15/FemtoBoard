from __future__ import annotations

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from antispam import services
from antispam.ip import get_client_ip
from boards.models import Board

_VALID_ACTIONS = {choice.value for choice in services.ActionType}


@require_POST
def issue_challenge(request: HttpRequest, board_code: str, action: str) -> HttpResponse:
    action = action.upper()
    if action not in _VALID_ACTIONS:
        return JsonResponse({"detail": "unknown action"}, status=400)

    board = get_object_or_404(Board, code=board_code, enabled=True)
    client_ip = get_client_ip(request)

    if not services.check_and_increment("pow_issue", client_ip, window_seconds=60, limit=30):
        return JsonResponse({"detail": "rate limited"}, status=429)

    difficulty = board.pow_difficulty_bits_for(action)
    issued = services.issue_challenge(
        board=board,
        action=action,
        client_ip=client_ip,
        difficulty_bits=difficulty,
        ttl_seconds=board.pow_challenge_ttl_seconds,
    )
    return JsonResponse(
        {
            "id": issued.id,
            "challenge": issued.challenge,
            "difficulty_bits": issued.difficulty_bits,
            "expires_at": issued.expires_at.isoformat(),
        }
    )
