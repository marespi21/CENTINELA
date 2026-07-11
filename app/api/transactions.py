"""Transactions API router.

Exposes ``POST /transactions``: validates the body, hands it to the service
(which persists to Blob Storage and publishes to the queue) and returns
``202 Accepted`` immediately. No fraud logic here.
"""

from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import get_settings
from app.infrastructure.azure.blob import BlobStorageClient
from app.infrastructure.azure.queue import QueueStorageClient
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.transaction import TransactionAccepted, TransactionCreate
from app.services.transaction_service import (
    TransactionPublishError,
    TransactionService,
)

router = APIRouter(tags=["transactions"])


@lru_cache
def _build_service() -> TransactionService:
    """Wire settings -> Azure clients -> repository -> service (once)."""
    settings = get_settings()
    blob = BlobStorageClient(settings.storage_connection_string)
    queue = QueueStorageClient(
        settings.storage_connection_string, settings.transactions_queue
    )
    repository = TransactionRepository(blob, queue, settings.transactions_container)
    return TransactionService(repository)


def get_transaction_service() -> TransactionService:
    """FastAPI dependency returning the cached TransactionService singleton."""
    return _build_service()


@router.post(
    "/transactions",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=TransactionAccepted,
    summary="Accept a transaction for asynchronous fraud processing",
)
def create_transaction(
    payload: TransactionCreate,
    service: TransactionService = Depends(get_transaction_service),
) -> TransactionAccepted:
    try:
        transaction = service.ingest(payload)
    except TransactionPublishError as exc:
        # Persisted but not queued: signal a retryable error. The client should
        # retry with the same transactionId (the operation is idempotent).
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
            headers={"Retry-After": "1"},
        ) from exc
    return TransactionAccepted(transactionId=transaction.transaction_id)
