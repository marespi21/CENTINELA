from __future__ import annotations

from app.domain.repositories.blob_storage import BlobStorage


class AzureBlobStorage(BlobStorage):
    """Adaptador de Azure Blob Storage.

    Se activa reemplazando InMemoryBlobStorage en el composition root
    (presentation/api/dependencies/documents.py) cuando el Storage Account
    y el container existan.

    Autenticación:
    - connection_string: para desarrollo/local.
    - account_url + Managed Identity (DefaultAzureCredential): en Azure,
      sin credenciales en código (entregable de Lukas).

    El SDK de Azure se importa de forma perezosa para no exigirlo mientras
    se trabaja con los adaptadores en memoria.
    """

    def __init__(
        self,
        container_name: str,
        connection_string: str | None = None,
        account_url: str | None = None,
    ) -> None:
        from azure.storage.blob import BlobServiceClient

        if connection_string:
            service = BlobServiceClient.from_connection_string(connection_string)
        elif account_url:
            from azure.identity import DefaultAzureCredential

            service = BlobServiceClient(
                account_url, credential=DefaultAzureCredential()
            )
        else:
            raise ValueError("connection_string or account_url is required")

        self._container = service.get_container_client(container_name)

    def upload(self, blob_name: str, data: bytes, content_type: str) -> str:
        from azure.storage.blob import ContentSettings

        self._container.upload_blob(
            name=blob_name,
            data=data,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type),
        )
        return self._container.get_blob_client(blob_name).url

    def download(self, blob_name: str) -> bytes:
        stream = self._container.download_blob(blob_name)
        return stream.readall()

    def exists(self, blob_name: str) -> bool:
        return self._container.get_blob_client(blob_name).exists()
