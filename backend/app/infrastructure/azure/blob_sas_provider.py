"""Acceso temporal a documentos vía SAS delegada por usuario (Semana 3).

Genera una SAS de **user delegation** (firmada con Managed Identity, no con la
clave de la cuenta) de solo lectura y con expiración corta. El contenedor sigue
privado; el analista recibe una URL que caduca. El SDK se importa perezosamente.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.domain.repositories.document_access_provider import (
    DocumentAccess,
    DocumentAccessProvider,
)


class AzureBlobSasProvider(DocumentAccessProvider):
    def __init__(self, account_url: str, account_name: str, container: str) -> None:
        self._account_url = account_url.rstrip("/")
        self._account_name = account_name
        self._container = container

    def temporary_read_url(self, blob_name: str, ttl_seconds: int = 300) -> DocumentAccess:
        from azure.identity import DefaultAzureCredential
        from azure.storage.blob import (
            BlobSasPermissions,
            BlobServiceClient,
            generate_blob_sas,
        )

        service = BlobServiceClient(
            self._account_url, credential=DefaultAzureCredential()
        )
        start = datetime.now(timezone.utc)
        expiry = start + timedelta(seconds=ttl_seconds)

        # Clave de delegación firmada por la Managed Identity (sin clave de cuenta).
        delegation_key = service.get_user_delegation_key(start, expiry)
        sas = generate_blob_sas(
            account_name=self._account_name,
            container_name=self._container,
            blob_name=blob_name,
            user_delegation_key=delegation_key,
            permission=BlobSasPermissions(read=True),
            start=start,
            expiry=expiry,
        )
        url = f"{self._account_url}/{self._container}/{blob_name}?{sas}"
        return DocumentAccess(url=url, expires_at=expiry)
