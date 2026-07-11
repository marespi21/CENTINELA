"""Repository for persisting uploaded files to Blob Storage."""

from __future__ import annotations

from app.infrastructure.azure.blob import BlobStorageClient


class UploadRepository:
    """Stores raw uploaded files in Blob Storage."""

    def __init__(self, blob: BlobStorageClient, container: str) -> None:
        self._blob = blob
        self._container = container

    def save(self, blob_name: str, data: bytes, content_type: str | None) -> str:
        """Store the file bytes as a blob; return the blob name."""
        return self._blob.upload_bytes(self._container, blob_name, data, content_type)
