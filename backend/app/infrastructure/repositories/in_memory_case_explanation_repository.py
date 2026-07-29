"""Explicaciones append-only en memoria (desarrollo/pruebas)."""

from __future__ import annotations

from app.domain.entities.explanation import Explanation
from app.domain.repositories.case_explanation_repository import (
    CaseExplanationRepository,
)


class InMemoryCaseExplanationRepository(CaseExplanationRepository):
    """Conserva TODAS las versiones, igual que la tabla real.

    `latest_for` devuelve la última, que es lo que hace el adaptador PostgreSQL
    al leer; así los tests reproducen la semántica de producción en vez de una
    simplificación cómoda.
    """

    def __init__(self) -> None:
        self._by_case: dict[str, list[Explanation]] = {}

    def append_explanation(self, case_id: str, explanation: Explanation) -> None:
        self._by_case.setdefault(case_id, []).append(explanation)

    def versions_for(self, case_id: str) -> list[Explanation]:
        return list(self._by_case.get(case_id, []))

    def latest_for(self, case_id: str) -> Explanation | None:
        versions = self._by_case.get(case_id)
        return versions[-1] if versions else None
