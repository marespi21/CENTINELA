"""Uploads API router.

Exposes ``POST /upload``: receives a multipart file, stores it in Blob Storage
via the upload service and returns ``201 Created`` with the blob name.
"""

from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends, File, UploadFile, status
from pydantic import BaseModel

from app.core.config import get_settings
from app.infrastructure.azure.blob import BlobStorageClient
from app.repositories.upload_repository import UploadRepository
from app.services.upload_service import UploadService

router = APIRouter(tags=["uploads"])


class UploadResponse(BaseModel):
    """201 response describing the stored upload."""

    blobName: str


@lru_cache
def _build_service() -> UploadService:
    """Wire settings -> Blob client -> repository -> service (once)."""
    settings = get_settings()
    blob = BlobStorageClient(settings.storage_connection_string)
    repository = UploadRepository(blob, settings.uploads_container)
    return UploadService(repository)


def get_upload_service() -> UploadService:
    """FastAPI dependency returning the cached UploadService singleton."""
    return _build_service()


@router.post(
    "/upload",
    status_code=status.HTTP_201_CREATED,
    response_model=UploadResponse,
    summary="Upload a file to Blob Storage",
)
def upload_file(
    file: UploadFile = File(...),
    service: UploadService = Depends(get_upload_service),
) -> UploadResponse:
    # Sync endpoint: FastAPI runs it in a threadpool, so the blocking file
    # read and Azure SDK calls do not block the event loop.
    data = file.file.read()
    blob_name = service.store(file.filename, data, file.content_type)
    return UploadResponse(blobName=blob_name)
