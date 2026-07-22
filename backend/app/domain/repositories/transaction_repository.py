from __future__ import annotations

from abc import ABC, abstractmethod
<<<<<<< HEAD

from backend.app.domain.entities.transaction import Transaction


class TransactionRepository(ABC):
    @abstractmethod
    async def save(self, tx: Transaction) -> None:
        """Persist a transaction.

        Semana 1: implementación in-memory.
        Semana 2+: implementación Azure Storage.
        """

        raise NotImplementedError

=======
from uuid import UUID

from app.domain.entities.transaction import Transaction


class TransactionRepository(ABC):
    """Puerto de persistencia de transacciones.

    La implementación concreta (memoria, Azure, etc.) vive en infrastructure.
    """

    @abstractmethod
    def save(self, transaction: Transaction) -> None:
        """Persiste la transacción recibida."""
        raise NotImplementedError

    @abstractmethod
    def exists(self, transaction_id: UUID) -> bool:
        """Indica si ya existe una transacción con ese id."""
        raise NotImplementedError
>>>>>>> e9a25c545a4bde0524846c6e6d2e9d6ae6f4e49e
