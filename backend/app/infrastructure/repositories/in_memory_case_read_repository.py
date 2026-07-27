"""Lectura de casos en memoria (desarrollo/pruebas).

Reemplaza al adaptador PostgreSQL en el composition root cuando no hay base de
datos de casos configurada. Permite sembrar casos para pruebas y para el
desarrollo local de la API de revisión.
"""

from __future__ import annotations

from app.domain.repositories.case_read_repository import CaseDetail, CaseReadRepository


class InMemoryCaseReadRepository(CaseReadRepository):
    def __init__(self, cases: list[CaseDetail] | None = None) -> None:
        self._by_id: dict[str, CaseDetail] = {}
        for case in cases or []:
            self.add(case)

    def add(self, case: CaseDetail) -> None:
        self._by_id[case.case_id] = case

    def get_case(self, case_id: str) -> CaseDetail | None:
        return self._by_id.get(case_id)
