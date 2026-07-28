"""Escritura de casos en memoria (desarrollo/pruebas).

Al persistir un caso construye su `CaseDetail` y, si se le pasa un repositorio de
lectura en memoria, lo inserta ahí — de modo que el consumidor (mensajería), la
API de lectura (casos) y las acciones del analista (asignar/resolver) queden
conectados de punta a punta en dev/test.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from uuid import uuid4

from app.domain.entities.opened_case import OpenedCase
from app.domain.exceptions.case_exceptions import CaseNotFoundError
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

    def assign_case(self, case_id: str, *, assignee_id: str, actor: str) -> None:
        detail = self._require(case_id)
        self._apply(
            detail,
            status="En Investigacion",
            assignee=assignee_id,
            audit={"accion": "UPDATE", "usuario": actor, "fecha": _now_iso()},
        )

    def resolve_case(
        self, case_id: str, *, resolution: str, note: str | None, actor: str
    ) -> None:
        detail = self._require(case_id)
        detalle = resolution if not note else f"{resolution} - {note}"
        self._apply(
            detail,
            status="Resuelto",
            assignee=detail.assignee,
            audit={
                "accion": "UPDATE",
                "usuario": actor,
                "fecha": _now_iso(),
                "detalle": detalle,
            },
        )

    def _require(self, case_id: str) -> CaseDetail:
        detail = self._read.get_case(case_id) if self._read is not None else None
        if detail is None:
            raise CaseNotFoundError(case_id)
        return detail

    def _apply(
        self,
        detail: CaseDetail,
        *,
        status: str,
        assignee: str | None,
        audit: dict,
    ) -> None:
        # La traza es append-only: nunca se altera lo previo.
        updated = replace(
            detail,
            status=status,
            assignee=assignee,
            audit_trail=[*detail.audit_trail, audit],
        )
        assert self._read is not None  # garantizado por _require
        self._read.add(updated)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
