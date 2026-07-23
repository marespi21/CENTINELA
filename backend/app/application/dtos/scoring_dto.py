from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.domain.entities.transaction import Transaction


def transaction_from_event(event: str | bytes | dict[str, Any]) -> Transaction:
    """Construye una `Transaction` a partir del evento de transacción.

    El evento es el mensaje que dispara la función serverless (contenido de la
    cola `transactions`). Contrato JSON (camelCase), alineado con el schema de
    ingesta:

        {
          "transactionId": "...", "accountId": "...", "amount": "150000.50",
          "currency": "COP", "merchantId": "...", "merchantCategory": "...",
          "timestamp": "2026-07-23T12:00:00Z",
          "latitude": "4.7110", "longitude": "-74.0721"
        }

    `timestamp` es opcional; si falta se usa el instante actual (UTC).
    """
    data: dict[str, Any] = event if isinstance(event, dict) else json.loads(event)

    raw_ts = data.get("timestamp")
    if raw_ts:
        timestamp = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
    else:
        timestamp = datetime.now(timezone.utc)

    return Transaction(
        transaction_id=UUID(str(data["transactionId"])),
        account_id=str(data["accountId"]),
        amount=Decimal(str(data["amount"])),
        currency=str(data["currency"]).upper(),
        merchant_id=str(data["merchantId"]),
        merchant_category=str(data["merchantCategory"]),
        timestamp=timestamp,
        latitude=Decimal(str(data["latitude"])),
        longitude=Decimal(str(data["longitude"])),
    )
