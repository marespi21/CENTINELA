from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Transaction:
    transaction_id: UUID
    account_id: str
    amount: float
    currency: str
    merchant_id: str
    merchant_category: str
    timestamp: datetime
    latitude: float
    longitude: float

