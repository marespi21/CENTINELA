"""Puerto de escritura de explicaciones de un caso (Sprint 6, Fase 4).

Puerto propio y estrecho en vez de un método más en `CaseWriteRepository`:
enriquecer una explicación no tiene nada que ver con abrir, asignar o resolver
un caso, y meterlo ahí obligaría a todos los implementadores del puerto grande
a cargar con una operación que no les incumbe.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.explanation import Explanation


class CaseExplanationRepository(ABC):
    @abstractmethod
    def append_explanation(self, case_id: str, explanation: Explanation) -> None:
        """Añade una versión de la explicación del caso.

        AÑADE, no reemplaza: `caso_explicaciones` es append-only y auditada, y
        la lectura toma siempre la más reciente. Así la explicación por reglas
        queda como traza de lo que se dijo primero.
        """
        raise NotImplementedError
