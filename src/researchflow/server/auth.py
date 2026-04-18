"""Optional Bearer-token auth dependency."""

from __future__ import annotations

from fastapi import Header, HTTPException, status

from researchflow.server.config import Settings


def make_auth_dependency(settings: Settings):
    """Build a FastAPI dependency that gates routes on the configured token.

    When `settings.api_token` is not set, the dependency is a no-op —
    allows unauthenticated usage for local / intra-cluster calls, same
    pattern as the sibling services.
    """

    async def _check(authorization: str | None = Header(default=None)):
        if not settings.api_token:
            return
        expected = f"Bearer {settings.api_token}"
        if authorization != expected:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="missing or invalid API token",
            )

    return _check
