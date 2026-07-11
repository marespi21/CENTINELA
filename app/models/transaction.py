"""Domain model for a transaction.

Field names are snake_case internally; :meth:`Transaction.to_storage_dict`
emits the canonical camelCase contract used for Blob persistence and the queue
message, so downstream consumers (the Week 2 Azure Functions) see the exact
shape that was accepted at the API boundary.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class Transaction(BaseModel):
    """Transaction entity flowing through service and repository layers."""

    transaction_id: UUID = Field(serialization_alias="transactionId")
    account_id: str = Field(serialization_alias="accountId")
    amount: float
    timestamp: datetime
    latitude: float
    longitude: float
    merchant: str
    category: str

    def to_storage_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dict in the canonical camelCase contract shape."""
        return self.model_dump(by_alias=True, mode="json")
