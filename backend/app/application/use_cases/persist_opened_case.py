"""Caso de uso: persistir un caso recibido de la cola `cases` (Semana 3).

Es el consumidor de mensajería (módulo Camila): parsea el mensaje y entrega el
caso a gestión de casos. La garantía de entrega la da la cola durable (Azure
Queue): si el consumidor está caído, el mensaje permanece hasta procesarse.
"""

from __future__ import annotations

import logging

from app.application.dtos.case_message_dto import opened_case_from_message
from app.domain.entities.opened_case import OpenedCase
from app.domain.repositories.case_write_repository import CaseWriteRepository
from app.domain.repositories.explanation_queue import ExplanationQueue

logger = logging.getLogger(__name__)


class PersistOpenedCaseUseCase:
    def __init__(
        self,
        case_write_repository: CaseWriteRepository,
        explanation_queue: ExplanationQueue | None = None,
    ) -> None:
        self._cases = case_write_repository
        self._explanations = explanation_queue

    def execute(self, message: str) -> str:
        """Parsea el mensaje del caso y lo persiste; devuelve el id del caso."""
        opened_case = opened_case_from_message(message)
        case_id = self._cases.save_opened_case(opened_case)
        self._request_enrichment(case_id, opened_case)
        return case_id

    def _request_enrichment(self, case_id: str, opened_case: OpenedCase) -> None:
        """Pide enriquecer la explicación, ya fuera del camino crítico.

        Se publica DESPUÉS de persistir por dos razones: el enriquecedor
        necesita el `case_id`, que solo existe una vez creado el caso; y así el
        caso ya está abierto y visible antes de que empiece nada lento.

        Un fallo aquí NO se propaga: el caso está guardado y el analista ya
        tiene su explicación por reglas. Tumbar el mensaje haría que la cola
        lo reintentara y se duplicaría el caso, que es mucho peor que quedarse
        sin una narrativa más bonita.
        """
        if self._explanations is None:
            return
        try:
            self._explanations.request_enrichment(
                case_id=case_id,
                transaction_id=opened_case.transaction_id,
                account_id=opened_case.account_id,
            )
        except Exception:  # noqa: BLE001 - el caso ya está a salvo
            logger.warning(
                "no se pudo pedir el enriquecimiento del caso %s; conserva su "
                "explicación por reglas",
                case_id,
                exc_info=True,
            )
