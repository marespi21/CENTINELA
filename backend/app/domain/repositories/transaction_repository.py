from __future__ import annotations

from abc import ABC, abstractmethod
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
