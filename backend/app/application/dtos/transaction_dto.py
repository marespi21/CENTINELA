from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class ReceiveTransactionInput:
    """Datos de entrada del caso de uso (independiente de HTTP)."""

    transaction_id: UUID
    account_id: str
    amount: Decimal
    currency: str
    merchant_id: str
    merchant_category: str
    latitude: Decimal
    longitude: Decimal


@dataclass(frozen=True)
class ReceiveTransactionOutput:
    """Resultado del caso de uso."""

    transaction_id: UUID
    status: str = "accepted"
