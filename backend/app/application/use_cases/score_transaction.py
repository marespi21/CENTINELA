from __future__ import annotations

from app.domain.entities.scoring_result import ScoringResult
from app.domain.entities.transaction import Transaction
from app.domain.repositories.case_queue import CaseQueue
from app.domain.repositories.score_repository import ScoreRepository
from app.domain.repositories.transaction_history_repository import (
    TransactionHistoryRepository,
)
from app.domain.services.scoring_engine import ScoringEngine
from app.domain.value_objects.scoring_config import ScoringConfig


class ScoreTransactionUseCase:
    """Motor de scoring disparado por el evento de transacción.

    Secuencia: consultar historial de la cuenta → evaluar las 4 reglas →
    sumar puntos → persistir score + detalle → publicar caso si supera el
    umbral. No se invoca desde la API: su disparador es el evento de la cola.
    """

    def __init__(
        self,
        history_repository: TransactionHistoryRepository,
        score_repository: ScoreRepository,
        case_queue: CaseQueue,
        config: ScoringConfig,
        engine: ScoringEngine | None = None,
    ) -> None:
        self._history = history_repository
        self._scores = score_repository
        self._cases = case_queue
        self._config = config
        self._engine = engine or ScoringEngine()

    def execute(self, transaction: Transaction) -> ScoringResult:
        history = self._history.history_for_account(transaction.account_id)
        result = self._engine.score(transaction, history, self._config)

        # Persistir score + detalle (valores observados por cada regla).
        self._scores.save(result)

        # Publicar caso solo si el score supera el umbral configurado.
        if result.is_case:
            self._cases.publish_case(result)

        return result
