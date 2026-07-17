from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class Transaction:
    """Transacción financiera a evaluar más adelante (Semana 2).

    Semana 1: solo se recibe, valida y persiste.
    """

    transaction_id: UUID
    account_id: str
    amount: Decimal
    currency: str
    merchant_id: str
    merchant_category: str
    timestamp: datetime
    latitude: Decimal
    longitude: Decimal