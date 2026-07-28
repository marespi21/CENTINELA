"""Puerto del índice de documentos de un caso (Semana 5).

Mapea un caso con los documentos de verificación que le pertenecen, para que la
consola pueda LISTARLOS. El acceso a cada documento sigue siendo por URL temporal
(SAS) a través de `DocumentAccessProvider`; este puerto solo dice CUÁLES existen.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CaseDocument:
    """Referencia a un documento de verificación de un caso (sin su contenido)."""

    blob_name: str
    filename: str
    content_type: str
    uploaded_at: datetime


class CaseDocumentRepository(ABC):
    @abstractmethod
    def list_for_case(self, case_id: str) -> list[CaseDocument]:
        """Documentos del caso (más reciente primero); [] si no tiene."""
        raise NotImplementedError
