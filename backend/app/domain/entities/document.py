from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class Document:
    """Documento (comprobante) recibido para procesamiento posterior.

    Semana 1: se almacena en Blob Storage y se notifica por Queue.
    """

    document_id: UUID
    filename: str
    content_type: str
    size_bytes: int
    blob_name: str
    uploaded_at: datetime
