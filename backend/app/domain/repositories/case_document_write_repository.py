"""Puerto de escritura del índice de documentos de un caso (Sprint 6, Fase 2).

`CaseDocumentRepository` solo sabía LEER, y nadie escribía: la tabla
`caso_documentos` existía vacía y `GET /cases/{id}/documents` devolvía siempre
lista vacía. Este puerto cierra ese hueco, y de paso guarda el veredicto de la
verificación documental junto a la referencia del documento.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from app.domain.entities.document_verification import DocumentVerification


class CaseDocumentWriteRepository(ABC):
    @abstractmethod
    def save_document(
        self,
        case_id: str,
        blob_name: str,
        filename: str,
        content_type: str,
        uploaded_at: datetime,
        verification: DocumentVerification | None = None,
    ) -> None:
        """Vincula el documento al caso y guarda su veredicto.

        Idempotente: reprocesar el mismo mensaje de cola (algo normal con
        entrega "al menos una vez") debe actualizar la fila, no duplicarla.
        """
        raise NotImplementedError
