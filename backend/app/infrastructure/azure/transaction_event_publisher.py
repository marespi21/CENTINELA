from __future__ import annotations

from app.application.dtos.transaction_event import transaction_to_event
from app.domain.entities.transaction import Transaction
from app.domain.repositories.transaction_event_publisher import (
    TransactionEventPublisher,
)
from app.infrastructure.azure.queue_service import AzureQueueService


class AzureTransactionEventPublisher(TransactionEventPublisher):
    """Publica el evento de transacción en Azure Queue Storage (`transactions`).

    La API solo espera a que la cola acepte el mensaje; el scoring lo procesa
    de forma asíncrona vía `queue_trigger`. Autenticación: connection string
    (local) o Managed Identity (producción).
    """

    def __init__(
        self,
        queue_name: str,
        connection_string: str | None = None,
        account_url: str | None = None,
    ) -> None:
        self._queue = AzureQueueService(
            queue_name=queue_name,
            connection_string=connection_string,
            account_url=account_url,
        )

    def publish(self, transaction: Transaction) -> None:
        self._queue.send_message(transaction_to_event(transaction))
