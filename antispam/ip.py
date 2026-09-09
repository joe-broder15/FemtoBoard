"""Trusted client IP resolution (design doc sections 45, 80.19).

Femtoboard defines exactly one way to determine a request's client IP:
``REMOTE_ADDR`` as seen by Django, walked back through at most
``FEMTOBOARD_TRUSTED_PROXY_COUNT`` reverse-proxy hops using the
``X-Forwarded-For`` header. A value of 0 (the default, used in
development) means REMOTE_ADDR is trusted directly and no forwarding
header is consulted at all -- this is safe only because the NixOS module
does not expose the application server to the public network.

Deployments behind exactly one reverse proxy set
FEMTOBOARD_TRUSTED_PROXY_COUNT=1, which trusts only the right-most entry
of X-Forwarded-For (the hop closest to the app server) and ignores
anything further left, since that portion of the header is
attacker-controlled.
"""

from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest


def get_client_ip(request: HttpRequest) -> str:
    trusted_hops: int = getattr(settings, "FEMTOBOARD_TRUSTED_PROXY_COUNT", 0)
    remote_addr: str = request.META.get("REMOTE_ADDR", "")

    if trusted_hops <= 0:
        return remote_addr

    forwarded_for: str = request.META.get("HTTP_X_FORWARDED_FOR", "")
    hops = [hop.strip() for hop in forwarded_for.split(",") if hop.strip()]

    if len(hops) < trusted_hops:
        # Fewer hops than expected: the proxy chain is misconfigured or the
        # header is missing. Fail closed to the directly-connecting peer
        # rather than trusting a possibly-spoofed header.
        return remote_addr

    result: str = hops[-trusted_hops]
    return result
