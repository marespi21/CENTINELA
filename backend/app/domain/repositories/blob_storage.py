from __future__ import annotations

from abc import ABC, abstractmethod


class BlobStorage(ABC):
    """Puerto de almacenamiento de documentos (Blob).

    La implementación concreta (memoria, Azure Blob Storage) vive en
    infrastructure. El caso de uso solo depende de este puerto.
    """

    @abstractmethod
    def upload(self, blob_name: str, data: bytes, content_type: str) -> str:
        """Sube el contenido y devuelve el identificador/URL del blob."""
        raise NotImplementedError

    @abstractmethod
    def download(self, blob_name: str) -> bytes:
        """Descarga y devuelve el contenido del blob."""
        raise NotImplementedError

    @abstractmethod
    def exists(self, blob_name: str) -> bool:
        """Indica si ya existe un blob con ese nombre."""
        raise NotImplementedError
