from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.entities.rule_result import RuleResult


@dataclass(frozen=True)
class ScoringResult:
    """Resultado del scoring de una transacción.

    Agrega el puntaje total, el umbral aplicado, el detalle por regla y si la
    transacción supera el umbral (y por tanto abre un caso).
    """

    transaction_id: UUID
    account_id: str
    score: int
    threshold: int
    rule_results: list[RuleResult]
    is_case: bool
    scored_at: datetime

    @property
    def triggered_rules(self) -> list[RuleResult]:
        """Solo las reglas que se activaron (con su detalle observado)."""
        return [r for r in self.rule_results if r.triggered]
