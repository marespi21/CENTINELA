from __future__ import annotations

from dataclasses import dataclass

from app.domain.repositories.blob_storage import BlobStorage


@dataclass
class _StoredBlob:
    data: bytes
    content_type: str


class InMemoryBlobStorage(BlobStorage):
    """Almacenamiento de blobs en memoria.

    Permite desarrollar y probar la subida de documentos sin Azure.
    Se reemplaza por AzureBlobStorage cambiando solo el composition root.
    """

    def __init__(self) -> None:
        self._blobs: dict[str, _StoredBlob] = {}

    def upload(self, blob_name: str, data: bytes, content_type: str) -> str:
        self._blobs[blob_name] = _StoredBlob(data=data, content_type=content_type)
        return blob_name

    def download(self, blob_name: str) -> bytes:
        return self._blobs[blob_name].data

    def exists(self, blob_name: str) -> bool:
        return blob_name in self._blobs
