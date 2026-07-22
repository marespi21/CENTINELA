from __future__ import annotations

from backend.app.application.use_cases.ingest_transaction import IngestTransactionUseCase
from backend.app.infrastructure.persistence.transaction_repository_inmemory import (
    InMemoryTransactionRepository,
)


class Container:
    def __init__(self) -> None:
        self.transaction_repository = InMemoryTransactionRepository()
        self.ingest_transaction_use_case = IngestTransactionUseCase(
            repository=self.transaction_repository
        )


def get_container() -> Container:
    # Singleton por proceso.
    # FastAPI crea múltiples workers; en Semana 2 se pensará para Azure/DI más robusto.
    # Para Semana 1 es suficiente.
    global _container  # type: ignore
    if "_container" not in globals():
        _container = Container()  # type: ignore
    return _container  # type: ignore

