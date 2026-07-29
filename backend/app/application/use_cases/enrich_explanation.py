"""Caso de uso: enriquecer la explicación de un caso ya abierto (Sprint 6, Fase 4).

Consume `explanation.requested` de la cola `explanations`. Para cuando llega,
el caso YA está abierto, persistido y visible en la bandeja con su explicación
por reglas: nada de lo que ocurra aquí puede retrasar la detección de fraude.

Es la mitad asíncrona del explicador. La otra mitad —barata, determinista y en
el camino crítico— sigue viviendo en `ScoreTransactionUseCase` y no se toca.

Errores, y por qué se tratan distinto:

- **Nada que enriquecer** (el enriquecedor devuelve None) → se descarta el
  mensaje sin escribir. Reintentar daría lo mismo.
- **Servicio caído** → se propaga para que el worker reintente.
- **Caso inexistente** → se descarta. Un caso borrado no se enriquece, y
  reintentar contra algo que no existe es un bucle.
"""

from __future__ import annotations

import logging

from app.application.dtos.explanation_request import explanation_request_from_message
from app.domain.entities.explanation import Explanation
from app.domain.entities.transaction import Transaction
from app.domain.repositories.case_explanation_repository import (
    CaseExplanationRepository,
)
from app.domain.repositories.case_read_repository import CaseReadRepository
from app.domain.repositories.transaction_history_repository import (
    TransactionHistoryRepository,
)
from app.domain.services.explanation_enricher import (
    EnrichmentContext,
    ExplanationEnricher,
)

logger = logging.getLogger(__name__)


class EnrichExplanationUseCase:
    def __init__(
        self,
        cases: CaseReadRepository,
        explanations: CaseExplanationRepository,
        enricher: ExplanationEnricher,
        history: TransactionHistoryRepository | None = None,
    ) -> None:
        self._cases = cases
        self._explanations = explanations
        self._enricher = enricher
        self._history = history

    def execute(self, message: str) -> Explanation | None:
        """Procesa una petición. Devuelve la explicación añadida, o None."""
        request = explanation_request_from_message(message)

        detail = self._cases.get_case(request.case_id)
        if detail is None:
            logger.warning(
                "se pidió enriquecer el caso %s, que no existe", request.case_id
            )
            return None

        context = EnrichmentContext(
            case_id=request.case_id,
            base_explanation=detail.explanation,
            transaction=self._find_transaction(request.account_id, request.transaction_id),
        )

        # Un ExplanationEnrichmentError sube y aborta: el worker reintentará.
        enriched = self._enricher.enrich(context)
        if enriched is None:
            logger.info(
                "sin enriquecimiento disponible para el caso %s; se conserva la "
                "explicación por reglas",
                request.case_id,
            )
            return None

        self._explanations.append_explanation(request.case_id, enriched)
        logger.info("explicación enriquecida para el caso %s", request.case_id)
        return enriched

    def _find_transaction(
        self, account_id: str, transaction_id: str
    ) -> Transaction | None:
        """Recupera la transacción para dar contexto al enriquecedor.

        Es opcional: sin ella el enriquecedor trabaja solo con la explicación
        base. Un fallo aquí no puede impedir el enriquecimiento.
        """
        if self._history is None or not account_id or not transaction_id:
            return None
        try:
            for transaction in self._history.history_for_account(account_id):
                if str(transaction.transaction_id) == transaction_id:
                    return transaction
        except Exception:  # noqa: BLE001 - contexto opcional, nunca bloqueante
            logger.debug("no se pudo recuperar la transacción", exc_info=True)
        return None
