from __future__ import annotations

from uuid import UUID

from app.domain.entities.scoring_result import ScoringResult
from app.domain.repositories.score_repository import ScoreRepository


class InMemoryScoreRepository(ScoreRepository):
    """Persistencia de scores en memoria (desarrollo/pruebas).

    Guarda el resultado completo, incluido el detalle observado por cada regla.
    """

    def __init__(self) -> None:
        self._scores: dict[UUID, ScoringResult] = {}

    def save(self, result: ScoringResult) -> None:
        self._scores[result.transaction_id] = result

    def get(self, transaction_id: UUID) -> ScoringResult | None:
        return self._scores.get(transaction_id)
