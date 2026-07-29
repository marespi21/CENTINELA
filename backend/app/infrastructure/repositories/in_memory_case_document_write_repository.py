"""Escritura del índice de documentos en memoria (desarrollo/pruebas).

Comparte almacén con `InMemoryCaseDocumentRepository` cuando se le pasa, de modo
que lo que verifica el worker se ve inmediatamente al listar los documentos del
caso — el mismo patrón que ya usaban los repositorios de casos en memoria.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.domain.entities.document_verification import DocumentVerification
from app.domain.repositories.case_document_repository import CaseDocument
from app.domain.repositories.case_document_write_repository import (
    CaseDocumentWriteRepository,
)
from app.infrastructure.repositories.in_memory_case_document_repository import (
    InMemoryCaseDocumentRepository,
)


class InMemoryCaseDocumentWriteRepository(CaseDocumentWriteRepository):
    def __init__(
        self, read_repository: InMemoryCaseDocumentRepository | None = None
    ) -> None:
        self._read = read_repository or InMemoryCaseDocumentRepository()

    @property
    def read_repository(self) -> InMemoryCaseDocumentRepository:
        return self._read

    def save_document(
        self,
        case_id: str,
        blob_name: str,
        filename: str,
        content_type: str,
        uploaded_at: datetime,
        verification: DocumentVerification | None = None,
    ) -> None:
        document = CaseDocument(
            blob_name=blob_name,
            filename=filename,
            content_type=content_type,
            uploaded_at=uploaded_at,
            verdict=verification.verdict.value if verification else None,
            verification_summary=verification.summary if verification else None,
            verified_at=datetime.now(timezone.utc) if verification else None,
        )
        # Idempotencia: la cola entrega "al menos una vez", así que reprocesar
        # el mismo blob debe sustituir la entrada, no duplicarla.
        self._read.upsert(case_id, document)
