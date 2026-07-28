"""Caso de uso: resolver un caso (Semana 5).

Registra la resolución (auditada), cambia el estado a Resuelto y devuelve el caso
actualizado.
"""

from __future__ import annotations

from app.domain.exceptions.case_exceptions import CaseNotFoundError
from app.domain.repositories.case_read_repository import CaseDetail, CaseReadRepository
from app.domain.repositories.case_write_repository import CaseWriteRepository


class ResolveCaseUseCase:
    def __init__(
        self,
        write_repository: CaseWriteRepository,
        read_repository: CaseReadRepository,
    ) -> None:
        self._write = write_repository
        self._read = read_repository

    def execute(
        self,
        case_id: str,
        *,
        resolution: str,
        note: str | None = None,
        actor: str,
    ) -> CaseDetail:
        self._write.resolve_case(
            case_id, resolution=resolution, note=note, actor=actor
        )
        detail = self._read.get_case(case_id)
        if detail is None:
            raise CaseNotFoundError(case_id)
        return detail
