from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.scoring_result import ScoringResult


class ScoreRepository(ABC):
    """Puerto de persistencia del score y su detalle de activación.

    Guarda el puntaje total junto con los valores concretos observados por
    cada regla (no solo el id de la regla). En producción es el mismo almacén
    NoSQL de la transacción (Cosmos DB).
    """

    @abstractmethod
    def save(self, result: ScoringResult) -> None:
        """Persiste el resultado del scoring con su detalle por regla."""
        raise NotImplementedError
