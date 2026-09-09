"""Runtime secret loading.

Secrets are provided as files at deployment time (never committed, never
baked into the Nix store) or, for local development only, as plain
environment variables. Production settings require the *_FILE form for
anything security-sensitive; see femtoboard.settings.prod.
"""

from __future__ import annotations

import os


class MissingSecretError(RuntimeError):
    """Raised when a required runtime secret is absent."""


def read_secret(env_var: str, *, required: bool = True, default: str | None = None) -> str | None:
    """Resolve a secret from ``{env_var}_FILE`` (preferred) or ``{env_var}``.

    Never logs the resolved value. Raises MissingSecretError if required
    and absent, rather than silently falling back to an insecure default.
    """
    file_path = os.environ.get(f"{env_var}_FILE")
    if file_path:
        try:
            with open(file_path, encoding="utf-8") as fh:
                value = fh.read().strip()
        except OSError as exc:
            raise MissingSecretError(f"Could not read secret file for {env_var}") from exc
        if not value and required:
            raise MissingSecretError(f"Secret file for {env_var} is empty")
        return value

    env_value = os.environ.get(env_var)
    if env_value:
        return env_value

    if required and default is None:
        raise MissingSecretError(f"Required secret {env_var} (or {env_var}_FILE) is not set")
    return default
