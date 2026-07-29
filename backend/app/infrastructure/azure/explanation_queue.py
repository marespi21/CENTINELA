"""Cola de enriquecimiento sobre Azure Queue Storage (Sprint 6, Fase 4)."""

from __future__ import annotations

from app.application.dtos.explanation_request import (
    ExplanationRequested,
    explanation_request_to_message,
)
from app.domain.repositories.explanation_queue import ExplanationQueue
from app.infrastructure.azure.queue_service import AzureQueueService


class AzureExplanationQueue(ExplanationQueue):
    """Publica peticiones de enriquecimiento en la cola `explanations`.

    Al construirse sobre `AzureQueueService`, hereda gratis la propagación del
    contexto de traza (Fase 3): el enriquecimiento cuelga de la misma traza que
    la transacción que abrió el caso.
    """

    def __init__(
        self,
        queue_name: str,
        connection_string: str | None = None,
        account_url: str | None = None,
    ) -> None:
        self._queue = AzureQueueService(
            queue_name=queue_name,
            connection_string=connection_string,
            account_url=account_url,
        )

    def request_enrichment(
        self, case_id: str, transaction_id: str, account_id: str
    ) -> None:
        self._queue.send_message(
            explanation_request_to_message(
                ExplanationRequested(
                    case_id=case_id,
                    transaction_id=transaction_id,
                    account_id=account_id,
                )
            )
        )
