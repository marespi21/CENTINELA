"""Composition root del acceso temporal a documentos (Semana 3, seguridad).

Con Storage configurado → SAS delegada por Managed Identity; sin configuración →
proveedor en memoria (dev/test).
"""

from __future__ import annotations

from functools import lru_cache

from app.domain.repositories.document_access_provider import DocumentAccessProvider
from app.infrastructure.config.settings import settings
from app.infrastructure.repositories.in_memory_document_access_provider import (
    InMemoryDocumentAccessProvider,
)


@lru_cache(maxsize=1)
def get_document_access_provider() -> DocumentAccessProvider:
    if settings.storage_account:
        from app.infrastructure.azure.blob_sas_provider import AzureBlobSasProvider

        return AzureBlobSasProvider(
            account_url=settings.blob_endpoint,
            account_name=settings.storage_account,
            container=settings.blob_container,
        )
    return InMemoryDocumentAccessProvider()
