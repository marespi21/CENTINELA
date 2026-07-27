"""Puerto de escritura de casos (Semana 3, gestión de casos).

Lo implementa el almacén relacional (PostgreSQL): al recibir un caso de la cola
`cases`, crea el caso y persiste su explicación de forma auditada e inmutable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.opened_case import OpenedCase


class CaseWriteRepository(ABC):
    @abstractmethod
    def save_opened_case(self, case: OpenedCase) -> str:
        """Persiste el caso y su explicación; devuelve el id del caso creado."""
        raise NotImplementedError
