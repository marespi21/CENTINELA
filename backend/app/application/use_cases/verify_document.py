"""Caso de uso: verificar un comprobante contra la transacción del caso.

Consume el evento `document.uploaded` de la cola `documents` —que hasta el
Sprint 6 Fase 2 no tenía consumidor y se perdía— y ejecuta la cadena completa:

    blob → OCR → contraste con la transacción → veredicto persistido

Errores, y por qué se tratan distinto:

- **Documento ilegible** → veredicto ILEGIBLE persistido. Es un resultado, no un
  fallo: reintentarlo daría exactamente lo mismo y solo gastaría cuota del OCR.
- **Servicio de OCR caído o sin cuota** → se propaga la excepción para que el
  worker NO borre el mensaje y lo reintente más tarde.
- **Caso o transacción inexistentes** → se registra el documento sin veredicto.
  El vínculo con el caso importa aunque no se pueda contrastar.
"""

from __future__ import annotations

import logging

from app.application.dtos.document_event import (
    DocumentUploadedEvent,
    document_event_from_message,
)
from app.domain.entities.document_verification import (
    DocumentVerification,
    VerificationVerdict,
)
from app.domain.entities.transaction import Transaction
from app.domain.repositories.blob_storage import BlobStorage
from app.domain.repositories.case_document_write_repository import (
    CaseDocumentWriteRepository,
)
from app.domain.repositories.case_read_repository import CaseReadRepository
from app.domain.repositories.document_analyzer import DocumentAnalyzer
from app.domain.repositories.transaction_history_repository import (
    TransactionHistoryRepository,
)
from app.domain.services.document_verifier import DocumentVerifier

logger = logging.getLogger(__name__)


class VerifyDocumentUseCase:
    def __init__(
        self,
        blob_storage: BlobStorage,
        analyzer: DocumentAnalyzer,
        verifier: DocumentVerifier,
        cases: CaseReadRepository,
        history: TransactionHistoryRepository,
        documents: CaseDocumentWriteRepository,
    ) -> None:
        self._blobs = blob_storage
        self._analyzer = analyzer
        self._verifier = verifier
        self._cases = cases
        self._history = history
        self._documents = documents

    def execute(self, message: str) -> DocumentVerification | None:
        """Procesa un mensaje de la cola. Devuelve el veredicto, o None si no aplica."""
        event = document_event_from_message(message)

        if event.case_id is None:
            logger.info(
                "documento %s subido sin caso asociado; no hay nada que contrastar",
                event.blob_name,
            )
            return None

        transaction = self._find_transaction(event)
        if transaction is None:
            # Se vincula igualmente: que la consola liste el documento importa
            # aunque no se haya podido emitir un veredicto.
            self._persist(event, None)
            return None

        content = self._blobs.download(event.blob_name)
        # Un DocumentAnalysisError sube y aborta: el worker reintentará.
        analysis = self._analyzer.analyze(content, event.content_type)
        verification = self._verifier.verify(analysis, transaction)

        self._persist(event, verification)
        logger.info(
            "documento verificado blob=%s caso=%s veredicto=%s",
            event.blob_name,
            event.case_id,
            verification.verdict.value,
        )
        return verification

    def _find_transaction(self, event: DocumentUploadedEvent) -> Transaction | None:
        """Localiza la transacción que originó el caso.

        Se resuelve con los puertos que ya existen: el caso da la cuenta y el id
        de transacción, y el historial de esa cuenta vive en una sola partición
        de Cosmos. Filtrar en memoria evita añadir una consulta nueva al almacén
        para un flujo que se ejecuta una vez por documento subido.
        """
        assert event.case_id is not None
        detail = self._cases.get_case(event.case_id)
        if detail is None:
            logger.warning(
                "el documento %s referencia el caso %s, que no existe",
                event.blob_name,
                event.case_id,
            )
            return None

        for transaction in self._history.history_for_account(detail.account_id):
            if str(transaction.transaction_id) == detail.transaction_id:
                return transaction

        logger.warning(
            "no se encontró la transacción %s de la cuenta %s en el historial",
            detail.transaction_id,
            detail.account_id,
        )
        return None

    def _persist(
        self, event: DocumentUploadedEvent, verification: DocumentVerification | None
    ) -> None:
        assert event.case_id is not None
        self._documents.save_document(
            case_id=event.case_id,
            blob_name=event.blob_name,
            filename=event.filename,
            content_type=event.content_type,
            uploaded_at=event.uploaded_at,
            verification=verification,
        )


__all__ = ["VerifyDocumentUseCase", "VerificationVerdict"]
