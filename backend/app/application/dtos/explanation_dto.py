"""Contrato de serialización de la explicación (Semana 3).

Fija la forma JSON (camelCase) con la que la explicación viaja por la cola de
casos (mensajería) y se persiste/expone (gestión de casos y API). Es el contrato
compartido: mensajería y casos consumen ESTA estructura.
"""

from __future__ import annotations

from datetime import timezone
from typing import Any

from app.domain.entities.explanation import Explanation


def serialize_explanation(explanation: Explanation) -> dict[str, Any]:
    """Explicación de dominio → dict JSON (camelCase)."""
    generated_at = explanation.generated_at
    if generated_at.tzinfo is None:
        generated_at = generated_at.replace(tzinfo=timezone.utc)
    return {
        "transactionId": str(explanation.transaction_id),
        "accountId": explanation.account_id,
        "score": explanation.score,
        "threshold": explanation.threshold,
        "isCase": explanation.is_case,
        "summary": explanation.summary,
        "generatedAt": generated_at.astimezone(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "reasons": [
            {
                "ruleId": reason.rule_id,
                "title": reason.title,
                "description": reason.description,
                "detail": reason.detail,
                "points": reason.points,
                "observed": reason.observed,
            }
            for reason in explanation.reasons
        ],
    }
