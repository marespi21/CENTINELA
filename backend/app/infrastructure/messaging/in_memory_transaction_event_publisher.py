from __future__ import annotations

from app.application.dtos.transaction_event import transaction_to_event
from app.domain.entities.transaction import Transaction
from app.domain.repositories.transaction_event_publisher import (
    TransactionEventPublisher,
)


class InMemoryTransactionEventPublisher(TransactionEventPublisher):
    """Publicador en memoria para desarrollo y pruebas de desacoplamiento.

    Conserva los eventos publicados. Si `consumer_enabled` es False, los
    mensajes quedan pendientes hasta reactivar el consumidor (simula cola
    durable con consumidor caído).
    """

    def __init__(self) -> None:
        self.published: list[str] = []
        self.pending: list[str] = []
        self.consumed: list[str] = []
        self.consumer_enabled: bool = True

    def publish(self, transaction: Transaction) -> None:
        event = transaction_to_event(transaction)
        self.published.append(event)
        self.pending.append(event)
        if self.consumer_enabled:
            self._drain()

    def stop_consumer(self) -> None:
        self.consumer_enabled = False

    def start_consumer(self) -> None:
        self.consumer_enabled = True
        self._drain()

    def _drain(self) -> None:
        while self.pending:
            self.consumed.append(self.pending.pop(0))
