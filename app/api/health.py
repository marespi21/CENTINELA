"""Health API router.

Exposes ``GET /health``: always returns ``200`` with the app status and a
basic Storage connectivity check. The overall status is ``degraded`` (still
HTTP 200) when Storage cannot be reached, so the endpoint doubles as a
liveness probe that reports readiness in its body.
"""

from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings
from app.infrastructure.azure.blob import BlobStorageClient

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Health payload returned by ``GET /health``."""

    status: str
    app: str
    version: str
    storage: str


@lru_cache
def _blob_client() -> BlobStorageClient:
    return BlobStorageClient(get_settings().storage_connection_string)


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness and Storage connectivity check",
)
def health() -> HealthResponse:
    settings = get_settings()
    storage_ok = _blob_client().check_connectivity()
    return HealthResponse(
        status="ok" if storage_ok else "degraded",
        app=settings.app_name,
        version=settings.app_version,
        storage="ok" if storage_ok else "unavailable",
    )
