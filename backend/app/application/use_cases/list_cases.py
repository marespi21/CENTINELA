"""Caso de uso: listar casos para la bandeja de la consola (Semana 5).

Normaliza los filtros y la paginación (defaults y topes) y delega en el puerto de
lectura. No conoce el motor de persistencia.
"""

from __future__ import annotations

from datetime import datetime

from app.domain.repositories.case_read_repository import (
    CaseListQuery,
    CasePage,
    CaseReadRepository,
)

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


class ListCasesUseCase:
    def __init__(self, read_repository: CaseReadRepository) -> None:
        self._read = read_repository

    def execute(
        self,
        *,
        status: str | None = None,
        assigned_to: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> CasePage:
        query = CaseListQuery(
            status=_clean(status),
            assigned_to=_clean(assigned_to),
            date_from=date_from,
            date_to=date_to,
            page=max(1, page),
            page_size=max(1, min(page_size, MAX_PAGE_SIZE)),
        )
        return self._read.list_cases(query)


def _clean(value: str | None) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None
