from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.transaction import Transaction


class TransactionEventPublisher(ABC):
    """Puerto de publicación del evento de transacción recibida.

    La API publica tras persistir y responde; el motor de scoring reacciona
    aparte (cola). Nunca se invoca el motor desde la API.
    """

    @abstractmethod
    def publish(self, transaction: Transaction) -> None:
        """Publica el evento de la transacción (garantía at-least-once)."""
        raise NotImplementedError
