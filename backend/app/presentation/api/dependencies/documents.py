from __future__ import annotations

from functools import lru_cache

from app.application.use_cases.upload_document import UploadDocumentUseCase
from app.domain.repositories.blob_storage import BlobStorage
from app.domain.repositories.document_queue import DocumentQueue
from app.infrastructure.config.settings import settings
from app.infrastructure.messaging.in_memory_queue import InMemoryQueue
from app.infrastructure.repositories.in_memory_blob_storage import InMemoryBlobStorage
from app.presentation.api.dependencies import get_secret_provider


def _azure_configured() -> bool:
    """Hay backend Azure si se definió una connection string o el nombre de cuenta.

    Sin nada configurado (dev/local) se usan los adaptadores en memoria.
    """
    return bool(settings.storage_connection_string or settings.storage_account)


def _resolve_storage_connection_string() -> str | None:
    """Resuelve la connection string de Storage.

    Prioridad:
    1. Key Vault (si está configurado).
    2. Variable de entorno STORAGE_CONNECTION_STRING.
    """
    if settings.key_vault_url:
        provider = get_secret_provider()
        vault_value = provider.get_secret("storage-connection-string")
        if vault_value:
            return vault_value
    return settings.storage_connection_string or None


@lru_cache(maxsize=1)
def get_blob_storage() -> BlobStorage:
    """Punto de composición del almacenamiento de documentos.

    - Con STORAGE_CONNECTION_STRING o STORAGE_ACCOUNT -> Azure Blob Storage.
    - Sin configuración -> memoria (dev/test).
    """
    if _azure_configured():
        from app.infrastructure.azure.blob_storage import AzureBlobStorage

        return AzureBlobStorage(
            container_name=settings.blob_container,
            connection_string=_resolve_storage_connection_string(),
            account_url=settings.blob_endpoint or None,
        )
    return InMemoryBlobStorage()


@lru_cache(maxsize=1)
def get_document_queue() -> DocumentQueue:
    """Punto de composición de la cola de documentos.

    - Con STORAGE_CONNECTION_STRING o STORAGE_ACCOUNT -> Azure Queue Storage.
    - Sin configuración -> memoria (dev/test).
    """
    if _azure_configured():
        from app.infrastructure.azure.queue_service import AzureQueueService

        return AzureQueueService(
            queue_name=settings.documents_queue,
            connection_string=_resolve_storage_connection_string(),
            account_url=settings.queue_endpoint or None,
        )
    return InMemoryQueue()


def get_upload_document_use_case() -> UploadDocumentUseCase:
    return UploadDocumentUseCase(
        blob_storage=get_blob_storage(),
        queue=get_document_queue(),
        allowed_content_types=settings.allowed_document_types_set,
        max_size_bytes=settings.max_document_bytes,
    )
