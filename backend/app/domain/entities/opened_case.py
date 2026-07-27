"""Caso abierto que llega por la cola `cases` para persistirse (Semana 3).

Es el dato que el consumidor de mensajería entrega a gestión de casos: la
transacción que originó el caso, su score y la explicación legible.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain.entities.explanation import Explanation


@dataclass(frozen=True)
class OpenedCase:
    transaction_id: str
    account_id: str
    score: int
    threshold: int
    explanation: Explanation
    opened_at: datetime
