from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class UploadDocumentInput:
    """Datos de entrada del caso de uso (independiente de HTTP)."""

    filename: str
    content_type: str
    content: bytes
    # Caso al que respalda el documento (Sprint 6, Fase 2). Opcional para no
    # romper a quien ya llama a POST /documents sin él: sin caso, el documento
    # se almacena pero no hay transacción contra la que contrastarlo.
    case_id: str | None = None


@dataclass(frozen=True)
class UploadDocumentOutput:
    """Resultado del caso de uso."""

    document_id: UUID
    blob_name: str
    status: str = "accepted"
