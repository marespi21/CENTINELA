from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.explanation import Explanation
from app.domain.entities.scoring_result import ScoringResult


class CaseQueue(ABC):
    """Puerto de publicación de casos de fraude.

    Cuando el score supera el umbral, el motor publica un caso (con el detalle
    de las reglas activadas y su explicación legible) para que el almacén
    relacional de casos lo procese.
    """

    @abstractmethod
    def publish_case(
        self, result: ScoringResult, explanation: Explanation | None = None
    ) -> None:
        """Publica un caso a partir del resultado de scoring y su explicación."""
        raise NotImplementedError
