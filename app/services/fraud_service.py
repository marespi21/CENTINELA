"""Fraud detection service - STUB (implemented in Week 2).

Intentionally not implemented in Week 1. The ``POST /transactions`` flow must
NOT perform any fraud evaluation: it only persists the transaction to Blob
Storage and enqueues a message. Fraud scoring will consume that queue via
Azure Functions in Week 2 and will be implemented in this module.
"""

from __future__ import annotations

from app.models.transaction import Transaction


class FraudService:
    """Placeholder for the Week 2 fraud-scoring service."""

    def evaluate(self, transaction: Transaction) -> None:
        """Score a transaction for fraud. Not implemented until Week 2."""
        raise NotImplementedError("Fraud scoring is implemented in Week 2.")
