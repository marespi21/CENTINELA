from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
<<<<<<< HEAD
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Transaction:
    transaction_id: UUID
    account_id: str
    amount: float
=======
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
>>>>>>> e9a25c545a4bde0524846c6e6d2e9d6ae6f4e49e
    currency: str
    merchant_id: str
    merchant_category: str
    timestamp: datetime
<<<<<<< HEAD
    latitude: float
    longitude: float

=======
    latitude: Decimal
    longitude: Decimal
>>>>>>> e9a25c545a4bde0524846c6e6d2e9d6ae6f4e49e
