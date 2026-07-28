"""Lectura de casos en memoria (desarrollo/pruebas).

Reemplaza al adaptador PostgreSQL en el composition root cuando no hay base de
datos de casos configurada. Permite sembrar casos para pruebas y para el
desarrollo local de la API de revisión y de la bandeja.
"""

from __future__ import annotations

from app.domain.repositories.case_read_repository import (
    CaseDetail,
    CaseListQuery,
    CasePage,
    CaseReadRepository,
    CaseSummary,
)


class InMemoryCaseReadRepository(CaseReadRepository):
    def __init__(self, cases: list[CaseDetail] | None = None) -> None:
        self._by_id: dict[str, CaseDetail] = {}
        for case in cases or []:
            self.add(case)

    def add(self, case: CaseDetail) -> None:
        self._by_id[case.case_id] = case

    def get_case(self, case_id: str) -> CaseDetail | None:
        return self._by_id.get(case_id)

    def list_cases(self, query: CaseListQuery) -> CasePage:
        matches = [c for c in self._by_id.values() if self._matches(c, query)]
        # Orden por fecha de apertura descendente (los más recientes primero).
        matches.sort(key=lambda c: c.opened_at, reverse=True)
        total = len(matches)
        window = matches[query.offset : query.offset + query.page_size]
        items = [self._to_summary(c) for c in window]
        return CasePage(
            items=items, total=total, page=query.page, page_size=query.page_size
        )

    @staticmethod
    def _matches(case: CaseDetail, query: CaseListQuery) -> bool:
        if query.status is not None and case.status.lower() != query.status.lower():
            return False
        if query.assigned_to is not None and case.assignee != query.assigned_to:
            return False
        if query.date_from is not None and case.opened_at < query.date_from:
            return False
        if query.date_to is not None and case.opened_at > query.date_to:
            return False
        return True

    @staticmethod
    def _to_summary(case: CaseDetail) -> CaseSummary:
        return CaseSummary(
            case_id=case.case_id,
            transaction_id=case.transaction_id,
            account_id=case.account_id,
            status=case.status,
            opened_at=case.opened_at,
            score=case.explanation.score,
            is_case=case.explanation.is_case,
            summary=case.explanation.summary,
            assignee=case.assignee,
        )
