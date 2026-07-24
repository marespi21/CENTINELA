from __future__ import annotations

import json
from datetime import datetime, timezone

from app.domain.entities.transaction import Transaction


def transaction_to_event(transaction: Transaction) -> str:
    """Serializa una transacción al contrato JSON de la cola `transactions`.

    Alineado con `transaction_from_event` (scoring) y el schema de ingesta
    (camelCase). Incluye `publishedAt` para demostrar desacoplamiento por
    marcas de tiempo (entregable 10).
    """
    published_at = datetime.now(timezone.utc)
    payload = {
        "event": "transaction.received",
        "transactionId": str(transaction.transaction_id),
        "accountId": transaction.account_id,
        "amount": str(transaction.amount),
        "currency": transaction.currency,
        "merchantId": transaction.merchant_id,
        "merchantCategory": transaction.merchant_category,
        "timestamp": transaction.timestamp.astimezone(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "latitude": str(transaction.latitude),
        "longitude": str(transaction.longitude),
        "publishedAt": published_at.isoformat().replace("+00:00", "Z"),
    }
    return json.dumps(payload)
