"""API schemas for the transactions endpoint (Pydantic v2).

``TransactionCreate`` is the request contract validated at the API boundary.
Its field set is fixed: no fields are added or removed, and unknown fields are
rejected (``extra="forbid"``).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TransactionCreate(BaseModel):
    """Incoming transaction contract."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "transactionId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "accountId": "acct-001",
                "amount": 149.90,
                "timestamp": "2026-07-13T14:32:00Z",
                "latitude": 4.7110,
                "longitude": -74.0721,
                "merchant": "Amazon",
                "category": "retail",
            }
        },
    )

    transactionId: UUID
    accountId: str = Field(min_length=1)
    amount: float = Field(gt=0, description="Transaction amount, must be positive")
    timestamp: datetime
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    merchant: str = Field(min_length=1)
    category: str = Field(min_length=1)


class TransactionAccepted(BaseModel):
    """202 acknowledgement returned once the transaction has been accepted."""

    transactionId: UUID
    status: str = "accepted"
