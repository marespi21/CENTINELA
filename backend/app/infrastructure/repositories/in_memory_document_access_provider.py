"""Acceso a documentos en memoria (desarrollo/pruebas).

Devuelve una URL temporal simulada, con expiración real, sin tocar Azure. Se
reemplaza por `AzureBlobSasProvider` en el composition root cuando hay Storage.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.domain.repositories.document_access_provider import (
    DocumentAccess,
    DocumentAccessProvider,
)


class InMemoryDocumentAccessProvider(DocumentAccessProvider):
    def temporary_read_url(self, blob_name: str, ttl_seconds: int = 300) -> DocumentAccess:
        expiry = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        url = f"https://local.dev/documents/{blob_name}?stub_token=dev&ttl={ttl_seconds}"
        return DocumentAccess(url=url, expires_at=expiry)
