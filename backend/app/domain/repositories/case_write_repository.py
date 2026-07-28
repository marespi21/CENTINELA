"""Puerto de escritura de casos (Semana 3 y 5, gestión de casos).

Lo implementa el almacén relacional (PostgreSQL):
- `save_opened_case`: al recibir un caso de la cola `cases`, crea el caso y
  persiste su explicación de forma auditada e inmutable (Semana 3).
- `assign_case` / `resolve_case`: acciones del analista desde la consola, que
  cambian el estado del caso dejando traza de auditoría inmutable (Semana 5).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.opened_case import OpenedCase


class CaseWriteRepository(ABC):
    @abstractmethod
    def save_opened_case(self, case: OpenedCase) -> str:
        """Persiste el caso y su explicación; devuelve el id del caso creado."""
        raise NotImplementedError

    @abstractmethod
    def assign_case(self, case_id: str, *, assignee_id: str, actor: str) -> None:
        """Asigna el caso a un analista. Lanza CaseNotFoundError si no existe."""
        raise NotImplementedError

    @abstractmethod
    def resolve_case(
        self, case_id: str, *, resolution: str, note: str | None, actor: str
    ) -> None:
        """Marca el caso como resuelto. Lanza CaseNotFoundError si no existe."""
        raise NotImplementedError
