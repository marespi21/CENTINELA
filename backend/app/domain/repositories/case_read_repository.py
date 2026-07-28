"""Puerto de lectura de casos para la API de analistas (Semana 3 y 5).

Lo IMPLEMENTA gestión de casos (almacén relacional): resuelve un caso por su
identificador (con su explicación y su traza de auditoría) y LISTA los casos con
filtros y paginación para la bandeja de la consola. La API depende solo de este
puerto, no del motor de persistencia.
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
    assignee: str | None = None


@dataclass(frozen=True)
class CaseSummary:
    """Fila de la bandeja de casos (vista compacta para la lista)."""

    case_id: str
    transaction_id: str
    account_id: str
    status: str
    opened_at: datetime
    score: int
    is_case: bool
    summary: str
    assignee: str | None = None


@dataclass(frozen=True)
class CaseListQuery:
    """Filtros y paginación de la lista de casos (ya normalizados)."""

    status: str | None = None
    assigned_to: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


@dataclass(frozen=True)
class CasePage:
    """Página de resultados de la bandeja."""

    items: list[CaseSummary]
    total: int
    page: int
    page_size: int


class CaseReadRepository(ABC):
    """Lectura de casos para la API de revisión y la bandeja."""

    @abstractmethod
    def get_case(self, case_id: str) -> CaseDetail | None:
        """Devuelve el caso o None si no existe."""
        raise NotImplementedError

    @abstractmethod
    def list_cases(self, query: CaseListQuery) -> CasePage:
        """Lista casos con filtros y paginación, ordenados por fecha desc."""
        raise NotImplementedError
