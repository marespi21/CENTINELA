from __future__ import annotations

from functools import lru_cache

from app.application.use_cases.receive_transaction import ReceiveTransactionUseCase
from app.domain.repositories.transaction_repository import TransactionRepository
from app.infrastructure.repositories.in_memory_transaction_repository import (
    InMemoryTransactionRepository,
)


@lru_cache(maxsize=1)
def get_transaction_repository() -> TransactionRepository:
    """Punto de composición de persistencia.

    Hoy: memoria.
    Después: otro integrante cambia solo esta función por Azure
    sin tocar routes ni use cases.
    """
    return InMemoryTransactionRepository()


def get_receive_transaction_use_case() -> ReceiveTransactionUseCase:
    return ReceiveTransactionUseCase(repository=get_transaction_repository())
