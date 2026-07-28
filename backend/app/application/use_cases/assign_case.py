"""Caso de uso: asignar un caso a un analista (Semana 5).

Escribe la asignación (auditada) y devuelve el caso actualizado. El identificador
del asignado se normaliza a UUID: si no llega uno válido, se deriva de forma
determinista del actor (uuid5), para soportar "asignarme" sin tabla de usuarios.
"""

from __future__ import annotations

from uuid import NAMESPACE_URL, UUID, uuid5

from app.domain.exceptions.case_exceptions import CaseNotFoundError
from app.domain.repositories.case_read_repository import CaseDetail, CaseReadRepository
from app.domain.repositories.case_write_repository import CaseWriteRepository


class AssignCaseUseCase:
    def __init__(
        self,
        write_repository: CaseWriteRepository,
        read_repository: CaseReadRepository,
    ) -> None:
        self._write = write_repository
        self._read = read_repository

    def execute(self, case_id: str, *, assignee: str, actor: str) -> CaseDetail:
        self._write.assign_case(case_id, assignee_id=coerce_uuid(assignee), actor=actor)
        detail = self._read.get_case(case_id)
        if detail is None:
            raise CaseNotFoundError(case_id)
        return detail


def coerce_uuid(value: str) -> str:
    """Devuelve `value` si ya es un UUID; si no, deriva uno estable (uuid5)."""
    try:
        return str(UUID(str(value)))
    except (ValueError, AttributeError, TypeError):
        return str(uuid5(NAMESPACE_URL, str(value)))
