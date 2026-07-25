"""Puerto del explicador (Semana 3).

Define la interfaz que transforma un `ScoringResult` en una `Explanation`
legible. La implementación de referencia vive en la capa de aplicación
(`RuleBasedExplainer`) y puede enriquecerse sin tocar a los consumidores del
contrato (mensajería, casos, API).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.explanation import Explanation
from app.domain.entities.scoring_result import ScoringResult


class Explainer(ABC):
    """Genera la explicación legible de una decisión de scoring."""

    @abstractmethod
    def explain(self, result: ScoringResult) -> Explanation:
        """Construye la `Explanation` a partir del resultado de scoring."""
        raise NotImplementedError
