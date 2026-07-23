from __future__ import annotations

from app.domain.entities.transaction import Transaction
from app.domain.repositories.transaction_history_repository import (
    TransactionHistoryRepository,
)


class InMemoryTransactionHistoryRepository(TransactionHistoryRepository):
    """Historial en memoria (desarrollo/pruebas).

    Se reemplaza por el adaptador de Cosmos DB en el composition root, sin
    tocar el caso de uso ni el motor de reglas.
    """

    def __init__(self, transactions: list[Transaction] | None = None) -> None:
        self._by_account: dict[str, list[Transaction]] = {}
        for transaction in transactions or []:
            self.add(transaction)

    def add(self, transaction: Transaction) -> None:
        self._by_account.setdefault(transaction.account_id, []).append(transaction)

    def history_for_account(self, account_id: str) -> list[Transaction]:
        return list(self._by_account.get(account_id, []))
