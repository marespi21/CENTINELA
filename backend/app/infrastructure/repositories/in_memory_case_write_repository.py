"""Escritura de casos en memoria (desarrollo/pruebas).

Al persistir un caso construye su `CaseDetail` y, si se le pasa un repositorio de
lectura en memoria, lo inserta ahí — de modo que el consumidor (mensajería) y la
API de lectura (casos) queden conectados de punta a punta en dev/test.
"""

from __future__ import annotations

from uuid import uuid4

from app.domain.entities.opened_case import OpenedCase
from app.domain.repositories.case_read_repository import CaseDetail
from app.domain.repositories.case_write_repository import CaseWriteRepository
from app.infrastructure.repositories.in_memory_case_read_repository import (
    InMemoryCaseReadRepository,
)


class InMemoryCaseWriteRepository(CaseWriteRepository):
    def __init__(self, read_repository: InMemoryCaseReadRepository | None = None) -> None:
        self._read = read_repository
        self.saved: list[CaseDetail] = []

    def save_opened_case(self, case: OpenedCase) -> str:
        case_id = str(uuid4())
        detail = CaseDetail(
            case_id=case_id,
            transaction_id=case.transaction_id,
            account_id=case.account_id,
            status="Abierto",
            opened_at=case.opened_at,
            explanation=case.explanation,
            audit_trail=[
                {
                    "accion": "INSERT",
                    "usuario": "svc-mensajeria",
                    "fecha": case.opened_at.isoformat(),
                }
            ],
        )
        self.saved.append(detail)
        if self._read is not None:
            self._read.add(detail)
        return case_id
