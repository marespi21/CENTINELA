"""Contrato del mensaje de la cola `documents` (Sprint 6, Fase 2).

Lo publica `UploadDocumentUseCase` y lo consume `VerifyDocumentUseCase`. Se
aísla aquí para que productor y consumidor compartan una única definición del
formato en vez de duplicar claves camelCase por el código.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class DocumentUploadedEvent:
    document_id: str
    blob_name: str
    filename: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime
    # Opcional: un documento puede subirse sin caso asociado. En ese supuesto
    # no hay transacción contra la que contrastar y no se verifica.
    case_id: str | None = None


def document_event_from_message(message: str) -> DocumentUploadedEvent:
    """Parsea el mensaje de la cola. Lanza ValueError si no cumple el contrato."""
    try:
        payload = json.loads(message)
    except json.JSONDecodeError as exc:
        raise ValueError(f"mensaje de documento no es JSON válido: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError("el mensaje de documento debe ser un objeto JSON")

    blob_name = payload.get("blobName")
    if not blob_name:
        raise ValueError("el mensaje de documento no trae 'blobName'")

    uploaded_at = payload.get("uploadedAt")
    parsed_at = _parse_datetime(uploaded_at) if uploaded_at else datetime.now(timezone.utc)

    case_id = payload.get("caseId") or None

    return DocumentUploadedEvent(
        document_id=str(payload.get("documentId", "")),
        blob_name=str(blob_name),
        filename=str(payload.get("filename", "")),
        content_type=str(payload.get("contentType", "application/octet-stream")),
        size_bytes=int(payload.get("sizeBytes", 0) or 0),
        uploaded_at=parsed_at,
        case_id=str(case_id) if case_id else None,
    )


def _parse_datetime(value: str) -> datetime:
    # `Z` es válido en ISO 8601 pero `fromisoformat` no lo aceptó hasta 3.11;
    # se normaliza para no depender de la versión del intérprete.
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return datetime.now(timezone.utc)
