"""Índice de documentos de casos en memoria (desarrollo/pruebas).

Permite sembrar los documentos de un caso para desarrollar y probar la lista de
la consola sin base de datos. Se reemplaza por el adaptador PostgreSQL cuando hay
base de casos configurada.
"""

from __future__ import annotations

from app.domain.repositories.case_document_repository import (
    CaseDocument,
    CaseDocumentRepository,
)


class InMemoryCaseDocumentRepository(CaseDocumentRepository):
    def __init__(self, by_case: dict[str, list[CaseDocument]] | None = None) -> None:
        self._by_case: dict[str, list[CaseDocument]] = {}
        for case_id, docs in (by_case or {}).items():
            for doc in docs:
                self.add(case_id, doc)

    def add(self, case_id: str, document: CaseDocument) -> None:
        self._by_case.setdefault(case_id, []).append(document)

    def list_for_case(self, case_id: str) -> list[CaseDocument]:
        docs = self._by_case.get(case_id, [])
        return sorted(docs, key=lambda d: d.uploaded_at, reverse=True)
