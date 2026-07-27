"""Puerto de acceso temporal a documentos de verificación (Semana 3, seguridad).

El analista no accede al contenedor directamente: obtiene una URL temporal y de
solo lectura (SAS delegada) para un documento concreto. El contenedor permanece
privado.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DocumentAccess:
    """URL temporal de lectura de un documento y su instante de expiración."""

    url: str
    expires_at: datetime


class DocumentAccessProvider(ABC):
    @abstractmethod
    def temporary_read_url(self, blob_name: str, ttl_seconds: int = 300) -> DocumentAccess:
        """Devuelve una URL temporal de solo lectura para el documento."""
        raise NotImplementedError
