"""Contrato del mensaje de la cola `explanations` (Sprint 6, Fase 4)."""

from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class ExplanationRequested:
    case_id: str
    transaction_id: str
    account_id: str


def explanation_request_to_message(request: ExplanationRequested) -> str:
    return json.dumps(
        {
            "event": "explanation.requested",
            "caseId": request.case_id,
            "transactionId": request.transaction_id,
            "accountId": request.account_id,
        }
    )


def explanation_request_from_message(message: str) -> ExplanationRequested:
    """Parsea el mensaje. Lanza ValueError si no cumple el contrato."""
    try:
        payload = json.loads(message)
    except json.JSONDecodeError as exc:
        raise ValueError(f"mensaje de explicación no es JSON válido: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError("el mensaje de explicación debe ser un objeto JSON")

    case_id = payload.get("caseId")
    if not case_id:
        raise ValueError("el mensaje de explicación no trae 'caseId'")

    return ExplanationRequested(
        case_id=str(case_id),
        transaction_id=str(payload.get("transactionId", "")),
        account_id=str(payload.get("accountId", "")),
    )
