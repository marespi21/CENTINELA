from __future__ import annotations

from functools import lru_cache

from app.application.use_cases.upload_document import UploadDocumentUseCase
from app.domain.repositories.blob_storage import BlobStorage
from app.domain.repositories.document_queue import DocumentQueue
from app.infrastructure.config.settings import settings
from app.infrastructure.messaging.in_memory_queue import InMemoryQueue
from app.infrastructure.repositories.in_memory_blob_storage import InMemoryBlobStorage


@lru_cache(maxsize=1)
def get_blob_storage() -> BlobStorage:
    """Punto de composición del almacenamiento de documentos.

    Hoy: memoria.
    Azure (cuando exista el Storage Account + container):
        from app.infrastructure.azure.blob_storage import AzureBlobStorage
        return AzureBlobStorage(
            container_name=settings.blob_container,
            connection_string=settings.storage_connection_string or None,
            account_url=settings.blob_endpoint or None,
        )
    """
    return InMemoryBlobStorage()


@lru_cache(maxsize=1)
def get_document_queue() -> DocumentQueue:
    """Punto de composición de la cola de documentos.

    Hoy: memoria.
    Azure (cuando exista la Queue):
        from app.infrastructure.azure.queue_service import AzureQueueService
        return AzureQueueService(
            queue_name=settings.documents_queue,
            connection_string=settings.storage_connection_string or None,
            account_url=settings.queue_endpoint or None,
        )
    """
    return InMemoryQueue()


def get_upload_document_use_case() -> UploadDocumentUseCase:
    return UploadDocumentUseCase(
        blob_storage=get_blob_storage(),
        queue=get_document_queue(),
        allowed_content_types=settings.allowed_document_types_set,
        max_size_bytes=settings.max_document_bytes,
    )
