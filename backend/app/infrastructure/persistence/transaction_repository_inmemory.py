from __future__ import annotations

import asyncio
from typing import Dict
from uuid import UUID

from backend.app.domain.entities.transaction import Transaction
from backend.app.domain.repositories.transaction_repository import TransactionRepository


class InMemoryTransactionRepository(TransactionRepository):
    """Repositorio in-memory para Semana 1.

    - Permite ejecutar la API y tests sin Azure.
    - No garantiza persistencia entre reinicios.
    """

    def __init__(self) -> None:
        self._store: Dict[UUID, Transaction] = {}
        self._lock = asyncio.Lock()

    async def save(self, tx: Transaction) -> None:
        async with self._lock:
            # Para Semana 1, aceptamos idempotencia básica por transaction_id.
            # Si llega el mismo transaction_id, se sobrescribe igual (misma semántica de ACK).
            self._store[tx.transaction_id] = tx

