"""Parseo del mensaje de la cola `cases` (Semana 3, mensajería).

Inverso del contrato que produce `AzureCaseQueue._serialize_case`: reconstruye
un `OpenedCase` (con su explicación) a partir del JSON del mensaje.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.application.dtos.explanation_dto import explanation_from_dict
from app.domain.entities.opened_case import OpenedCase


def opened_case_from_message(message: str | bytes | dict[str, Any]) -> OpenedCase:
    data: dict[str, Any] = (
        message if isinstance(message, dict) else json.loads(message)
    )

    if not data.get("explanation"):
        raise ValueError("case message without explanation")

    raw_ts = str(data["scoredAt"]).replace("Z", "+00:00")
    opened_at = datetime.fromisoformat(raw_ts)
    if opened_at.tzinfo is None:
        opened_at = opened_at.replace(tzinfo=timezone.utc)

    return OpenedCase(
        transaction_id=str(data["transactionId"]),
        account_id=str(data["accountId"]),
        score=int(data["score"]),
        threshold=int(data["threshold"]),
        explanation=explanation_from_dict(data["explanation"]),
        opened_at=opened_at,
    )
