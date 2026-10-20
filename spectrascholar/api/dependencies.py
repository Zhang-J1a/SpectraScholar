"""Shared FastAPI dependencies."""
from __future__ import annotations

import secrets

from fastapi import Header, HTTPException

from ..settings import settings


async def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    """Optional single-key protection for public deployments.

    This is deliberately simple: it protects a single-user demo, not a
    multi-tenant product.  Leave ``API_KEY`` empty for local use.
    """
    if not settings.api_key:
        return
    if not x_api_key or not secrets.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(
            status_code=401,
            detail="缺少或无效的 X-API-Key",
            headers={"WWW-Authenticate": "X-API-Key"},
        )
