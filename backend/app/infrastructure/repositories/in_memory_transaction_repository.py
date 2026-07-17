from __future__ import annotations

from uuid import UUID

from app.domain.entities.transaction import Transaction
from app.domain.repositories.transaction_repository import TransactionRepository


class InMemoryTransactionRepository(TransactionRepository):
    """Repositorio temporal en memoria.

    Permite desarrollar y probar la API sin Azure.
    Otro integrante reemplazará esta implementación por Azure Storage/Queue
    sin cambiar endpoints ni el caso de uso.
    """

    def __init__(self) -> None:
        self._transactions: dict[UUID, Transaction] = {}

    def save(self, transaction: Transaction) -> None:
        self._transactions[transaction.transaction_id] = transaction

    def exists(self, transaction_id: UUID) -> bool:
        return transaction_id in self._transactions
