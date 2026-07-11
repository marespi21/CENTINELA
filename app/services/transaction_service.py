"""Application service for transaction ingestion.

Maps the validated request to the domain model, persists it to Blob Storage
and enqueues it for asynchronous processing. The endpoint then returns 202.

NO fraud logic runs here. Fraud scoring lives in
:mod:`app.services.fraud_service` and is implemented in Week 2, consuming the
queue via Azure Functions.
"""

from __future__ import annotations

from uuid import UUID

from app.core.logger import get_logger
from app.models.transaction import Transaction
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.transaction import TransactionCreate

logger = get_logger(__name__)


class TransactionPublishError(RuntimeError):
    """Raised when a transaction was persisted but could not be published.

    The blob is durably stored but the queue message is missing. The
    transaction is safe to retry with the SAME ``transactionId``: ``save()``
    overwrites the same blob (idempotent) and ``publish()`` is retried. The
    Week 2 queue consumer must deduplicate by ``transactionId``.
    """

    def __init__(self, transaction_id: UUID) -> None:
        self.transaction_id = transaction_id
        super().__init__(
            f"Transaction {transaction_id} was persisted but could not be "
            "published to the queue; retry with the same transactionId."
        )


class TransactionService:
    """Orchestrates persistence and publication of incoming transactions."""

    def __init__(self, repository: TransactionRepository) -> None:
        self._repository = repository

    def ingest(self, payload: TransactionCreate) -> Transaction:
        """Persist and enqueue the transaction; return the domain entity."""
        transaction = Transaction(
            transaction_id=payload.transactionId,
            account_id=payload.accountId,
            amount=payload.amount,
            timestamp=payload.timestamp,
            latitude=payload.latitude,
            longitude=payload.longitude,
            merchant=payload.merchant,
            category=payload.category,
        )

        # Persist first (durable record), then publish for downstream workers.
        blob_name = self._repository.save(transaction)
        try:
            self._repository.publish(transaction)
        except Exception as exc:
            # The blob is persisted but the queue message is missing. Log the
            # inconsistency with the transactionId so ops can spot orphaned
            # (persisted-but-unpublished) transactions, and signal a retryable
            # error to the caller.
            logger.error(
                "Transaction persisted but publish failed",
                extra={
                    "transactionId": str(transaction.transaction_id),
                    "blob": blob_name,
                    "persisted": True,
                    "published": False,
                },
                exc_info=exc,
            )
            raise TransactionPublishError(transaction.transaction_id) from exc

        logger.info(
            "Transaction accepted",
            extra={
                "transactionId": str(transaction.transaction_id),
                "blob": blob_name,
                "persisted": True,
                "published": True,
            },
        )
        return transaction
