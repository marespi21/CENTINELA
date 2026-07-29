"""Puerto del explicador enriquecido (Sprint 6, Fase 4).

`Explainer` (semana 3) genera la explicación **barata y determinista** a partir
del `ScoringResult`: plantillas sobre el catálogo de reglas, microsegundos. Esa
sigue en el camino crítico y no se toca — es la que garantiza que ningún caso
llegue jamás sin explicación.

Este puerto es para la explicación **cara**: la que consulta un servicio externo
para redactar una narrativa más rica. Al ser lenta y poder fallar, se ejecuta
fuera del camino crítico, después de que el caso ya esté abierto y visible.

El enriquecimiento es aditivo, nunca destructivo: `caso_explicaciones` es
append-only y auditada, así que se añade una versión nueva y la anterior queda
como traza. Si el enriquecimiento falla, el analista conserva la explicación
por reglas.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.domain.entities.explanation import Explanation
from app.domain.entities.transaction import Transaction


class ExplanationEnrichmentError(Exception):
    """El servicio de enriquecimiento falló.

    Se distingue de "no hay nada que enriquecer": esto es un fallo transitorio
    (servicio caído, cuota, timeout) y el mensaje debe reintentarse.
    """


@dataclass(frozen=True)
class EnrichmentContext:
    """Todo lo que el enriquecedor necesita para redactar.

    Se le pasa la explicación base en vez de el `ScoringResult` porque en este
    punto del flujo el resultado del motor ya no existe: el caso está
    persistido y lo que hay es su explicación por reglas.
    """

    case_id: str
    base_explanation: Explanation
    transaction: Transaction | None = None


class ExplanationEnricher(ABC):
    @abstractmethod
    def enrich(self, context: EnrichmentContext) -> Explanation | None:
        """Devuelve una explicación enriquecida, o None si no hay nada que añadir.

        Lanza `ExplanationEnrichmentError` si el fallo es del servicio.
        """
        raise NotImplementedError
