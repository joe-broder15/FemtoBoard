from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser

from moderation.models import ModerationAction


def record_action(
    *,
    actor: AbstractBaseUser | AnonymousUser | None,
    verb: str,
    target: str,
    reason: str = "",
) -> ModerationAction:
    """Write one append-only audit log entry.

    Never includes passwords, tripcode secrets, session data, or other
    sensitive values (design doc 80.22) -- callers must only pass safe,
    already-summarized text in ``target``/``reason``.
    """
    actor_id = (
        getattr(actor, "pk", None)
        if actor is not None and getattr(actor, "is_authenticated", False)
        else None
    )
    return ModerationAction.objects.create(
        actor_id=actor_id,
        verb=verb,
        target=target,
        reason=reason,
    )
