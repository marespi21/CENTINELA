"""Azure Blob Storage client wrapper.

A thin gateway over ``azure-storage-blob`` used by the repository layer. The
underlying service client is created lazily and the target container is
ensured (created if missing) before every write, so the app can boot even if
Storage is momentarily unavailable.
"""

from __future__ import annotations

import json
from typing import Any

from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import BlobServiceClient, ContentSettings

from app.core.logger import get_logger

logger = get_logger(__name__)


class BlobStorageClient:
    """Minimal Blob Storage gateway (ensure container, upload blobs)."""

    def __init__(self, connection_string: str) -> None:
        self._connection_string = connection_string
        self._service: BlobServiceClient | None = None

    @property
    def service(self) -> BlobServiceClient:
        if self._service is None:
            self._service = BlobServiceClient.from_connection_string(
                self._connection_string
            )
        return self._service

    def ensure_container(self, container: str) -> None:
        """Create the container if it does not already exist (idempotent)."""
        try:
            self.service.create_container(container)
            logger.info("Created blob container", extra={"container": container})
        except ResourceExistsError:
            pass

    def upload_json(
        self, container: str, blob_name: str, payload: dict[str, Any]
    ) -> str:
        """Serialize ``payload`` to JSON, upload it, and return the blob name."""
        self.ensure_container(container)
        data = json.dumps(payload, default=str).encode("utf-8")
        self.service.get_blob_client(container=container, blob=blob_name).upload_blob(
            data,
            overwrite=True,
            content_settings=ContentSettings(content_type="application/json"),
        )
        logger.info(
            "Uploaded JSON blob", extra={"container": container, "blob": blob_name}
        )
        return blob_name

    def upload_bytes(
        self,
        container: str,
        blob_name: str,
        data: bytes,
        content_type: str | None = None,
    ) -> str:
        """Upload raw bytes as a blob and return the blob name."""
        self.ensure_container(container)
        settings = ContentSettings(content_type=content_type) if content_type else None
        self.service.get_blob_client(container=container, blob=blob_name).upload_blob(
            data, overwrite=True, content_settings=settings
        )
        logger.info("Uploaded blob", extra={"container": container, "blob": blob_name})
        return blob_name

    def check_connectivity(self) -> bool:
        """Best-effort connectivity probe used by the health endpoint."""
        try:
            self.service.get_service_properties()
            return True
        except Exception:  # noqa: BLE001 - a health probe must never raise
            logger.warning("Blob storage connectivity check failed")
            return False
