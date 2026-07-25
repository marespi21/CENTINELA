"""Puerto de lectura de casos para la API de analistas (Semana 3).

Lo IMPLEMENTA gestión de casos (almacén relacional): resuelve un caso por su
identificador, con su explicación y su traza de auditoría. La API de revisión de
casos depende solo de este puerto, no del motor de persistencia.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.domain.entities.explanation import Explanation


@dataclass(frozen=True)
class CaseDetail:
    """Vista de lectura de un caso para el analista."""

    case_id: str
    transaction_id: str
    account_id: str
    status: str
    opened_at: datetime
    explanation: Explanation
    audit_trail: list[dict[str, Any]] = field(default_factory=list)


class CaseReadRepository(ABC):
    """Lectura de casos para la API de revisión."""

    @abstractmethod
    def get_case(self, case_id: str) -> CaseDetail | None:
        """Devuelve el caso o None si no existe."""
        raise NotImplementedError
