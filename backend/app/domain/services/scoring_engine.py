from __future__ import annotations

from datetime import datetime, timezone

from app.domain.entities.scoring_result import ScoringResult
from app.domain.entities.transaction import Transaction
from app.domain.services.rules import ALL_RULES
from app.domain.value_objects.scoring_config import ScoringConfig


class ScoringEngine:
    """Evalúa las 4 reglas, suma los puntos y decide si se abre un caso.

    Lógica de dominio pura: no toca red, persistencia ni colas.
    """

    def __init__(self, rules=ALL_RULES) -> None:
        self._rules = rules

    def score(
        self,
        transaction: Transaction,
        history: list[Transaction],
        config: ScoringConfig,
    ) -> ScoringResult:
        rule_results = [rule(transaction, history, config) for rule in self._rules]
        total = sum(r.points for r in rule_results)
        return ScoringResult(
            transaction_id=transaction.transaction_id,
            account_id=transaction.account_id,
            score=total,
            threshold=config.threshold,
            rule_results=rule_results,
            is_case=total >= config.threshold,
            scored_at=datetime.now(timezone.utc),
        )
