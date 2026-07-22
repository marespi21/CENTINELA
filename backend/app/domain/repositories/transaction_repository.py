from __future__ import annotations

from abc import ABC, abstractmethod

from backend.app.domain.entities.transaction import Transaction


class TransactionRepository(ABC):
    @abstractmethod
    async def save(self, tx: Transaction) -> None:
        """Persist a transaction.

        Semana 1: implementación in-memory.
        Semana 2+: implementación Azure Storage.
        """

        raise NotImplementedError

