from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.scoring_result import ScoringResult


class CaseQueue(ABC):
    """Puerto de publicación de casos de fraude.

    Cuando el score supera el umbral, el motor publica un caso (con el detalle
    de las reglas activadas) para que el almacén relacional de casos lo procese.
    """

    @abstractmethod
    def publish_case(self, result: ScoringResult) -> None:
        """Publica un caso a partir del resultado de scoring."""
        raise NotImplementedError
