from __future__ import annotations

from functools import lru_cache

from app.application.use_cases.receive_transaction import ReceiveTransactionUseCase
from app.domain.repositories.transaction_event_publisher import (
    TransactionEventPublisher,
)
from app.domain.repositories.transaction_repository import TransactionRepository
from app.infrastructure.config.settings import settings
from app.infrastructure.messaging.in_memory_transaction_event_publisher import (
    InMemoryTransactionEventPublisher,
)
from app.infrastructure.repositories.in_memory_transaction_repository import (
    InMemoryTransactionRepository,
)


def _azure_configured() -> bool:
    """Hay backend Azure si se definió connection string o nombre de cuenta."""
    return bool(settings.storage_connection_string or settings.storage_account)


@lru_cache(maxsize=1)
def get_transaction_repository() -> TransactionRepository:
    """Punto de composición de persistencia (módulo Camila — historial real).

    - Con COSMOS_ENDPOINT -> Cosmos DB (pk /accountId) para alimentar el historial.
    - Sin configuración -> memoria (dev/test).
    """
    if settings.cosmos_configured:
        from app.infrastructure.azure.cosmos_transaction_repository import (
            CosmosTransactionRepository,
        )

        return CosmosTransactionRepository(
            endpoint=settings.cosmos_endpoint,
            database=settings.cosmos_database,
            container=settings.cosmos_container,
            key=settings.cosmos_key or None,
        )
    return InMemoryTransactionRepository()


@lru_cache(maxsize=1)
def get_transaction_event_publisher() -> TransactionEventPublisher:
    """Punto de composición de la mensajería de transacciones (módulo Camila).

    - Con STORAGE_CONNECTION_STRING o STORAGE_ACCOUNT -> Azure Queue `transactions`.
    - Sin configuración -> memoria (dev/test), con soporte de pause/resume.
    """
    if _azure_configured():
        from app.infrastructure.azure.transaction_event_publisher import (
            AzureTransactionEventPublisher,
        )

        return AzureTransactionEventPublisher(
            queue_name=settings.transactions_queue,
            connection_string=settings.storage_connection_string or None,
            account_url=settings.queue_endpoint or None,
        )
    return InMemoryTransactionEventPublisher()


def get_receive_transaction_use_case() -> ReceiveTransactionUseCase:
    return ReceiveTransactionUseCase(
        repository=get_transaction_repository(),
        event_publisher=get_transaction_event_publisher(),
    )
