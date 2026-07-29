"""Puerto de la cola de enriquecimiento de explicaciones (Sprint 6, Fase 4).

Separa el momento en que el caso queda abierto y visible del momento en que su
explicación se enriquece. El caso NO espera al enriquecimiento.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class ExplanationQueue(ABC):
    @abstractmethod
    def request_enrichment(
        self, case_id: str, transaction_id: str, account_id: str
    ) -> None:
        """Pide enriquecer la explicación de un caso ya persistido.

        Se publica DESPUÉS de persistir porque el enriquecedor necesita el
        `case_id`, que solo existe una vez creado el caso.
        """
        raise NotImplementedError
