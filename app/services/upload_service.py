"""Application service for file uploads.

Generates a collision-free blob name from the uploaded file and delegates
persistence to the repository.
"""

from __future__ import annotations

from pathlib import PurePosixPath
from uuid import uuid4

from app.core.logger import get_logger
from app.repositories.upload_repository import UploadRepository

logger = get_logger(__name__)


class UploadService:
    """Names and stores uploaded files in Blob Storage."""

    def __init__(self, repository: UploadRepository) -> None:
        self._repository = repository

    def store(
        self, filename: str | None, data: bytes, content_type: str | None
    ) -> str:
        """Store an uploaded file and return the generated blob name."""
        # Strip any path components (handling both separators) and prefix a
        # UUID so concurrent uploads of the same filename never collide.
        base = PurePosixPath(filename.replace("\\", "/")).name if filename else ""
        base = base or "upload"
        blob_name = f"{uuid4().hex}-{base}"

        stored = self._repository.save(blob_name, data, content_type)
        logger.info("File uploaded", extra={"blob": stored, "size": len(data)})
        return stored
