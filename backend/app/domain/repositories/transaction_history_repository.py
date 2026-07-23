from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.transaction import Transaction


class TransactionHistoryRepository(ABC):
    """Puerto de lectura del historial de transacciones por cuenta.

    En producción lo implementa el almacén NoSQL (Cosmos DB), donde la
    consulta por `account_id` toca una sola partición (ver docs/nosql.md).
    """

    @abstractmethod
    def history_for_account(self, account_id: str) -> list[Transaction]:
        """Devuelve las transacciones previas de la cuenta."""
        raise NotImplementedError
