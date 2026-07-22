from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import PurePosixPath
from uuid import UUID, uuid4

from app.application.dtos.document_dto import (
    UploadDocumentInput,
    UploadDocumentOutput,
)
from app.domain.exceptions.document_exceptions import (
    DocumentTooLargeError,
    EmptyDocumentError,
    InvalidDocumentTypeError,
)
from app.domain.repositories.blob_storage import BlobStorage
from app.domain.repositories.document_queue import DocumentQueue


class UploadDocumentUseCase:
    """Sube un documento a Blob Storage y publica un evento en la Queue.

    Reglas Semana 1:
    - Valida que el archivo no esté vacío y no exceda el tamaño máximo.
    - Valida que el tipo de contenido esté permitido.
    - Genera un nombre único (UUID) preservando la extensión original.
    - Sube a Blob y luego notifica por Queue para procesamiento posterior.
    """

    def __init__(
        self,
        blob_storage: BlobStorage,
        queue: DocumentQueue,
        allowed_content_types: frozenset[str],
        max_size_bytes: int,
    ) -> None:
        self._blob_storage = blob_storage
        self._queue = queue
        self._allowed_content_types = allowed_content_types
        self._max_size_bytes = max_size_bytes

    def execute(self, data: UploadDocumentInput) -> UploadDocumentOutput:
        self._validate_size(data.content)
        self._validate_type(data.content_type)

        document_id = uuid4()
        blob_name = self._generate_name(document_id, data.filename)

        self._blob_storage.upload(blob_name, data.content, data.content_type)

        uploaded_at = datetime.now(timezone.utc)
        self._queue.send_message(
            json.dumps(
                {
                    "event": "document.uploaded",
                    "documentId": str(document_id),
                    "blobName": blob_name,
                    "filename": data.filename,
                    "contentType": data.content_type,
                    "sizeBytes": len(data.content),
                    "uploadedAt": uploaded_at.isoformat(),
                }
            )
        )

        return UploadDocumentOutput(document_id=document_id, blob_name=blob_name)

    def _validate_size(self, content: bytes) -> None:
        if not content:
            raise EmptyDocumentError()
        if len(content) > self._max_size_bytes:
            raise DocumentTooLargeError(len(content), self._max_size_bytes)

    def _validate_type(self, content_type: str) -> None:
        if content_type not in self._allowed_content_types:
            raise InvalidDocumentTypeError(content_type)

    def _generate_name(self, document_id: UUID, filename: str) -> str:
        suffix = PurePosixPath(filename).suffix.lower()
        return f"{document_id}{suffix}"
