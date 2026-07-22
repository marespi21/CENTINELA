from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class UploadDocumentInput:
    """Datos de entrada del caso de uso (independiente de HTTP)."""

    filename: str
    content_type: str
    content: bytes


@dataclass(frozen=True)
class UploadDocumentOutput:
    """Resultado del caso de uso."""

    document_id: UUID
    blob_name: str
    status: str = "accepted"
