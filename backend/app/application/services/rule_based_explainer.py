"""Implementación de referencia del explicador (Semana 3).

Convierte un `ScoringResult` en una `Explanation` legible usando el catálogo de
reglas y los valores observados de cada regla activada. Es una BASE funcional y
verificable que fija el contrato para el resto del equipo; puede enriquecerse
(más matices, texto por idioma, etc.) sin romper a los consumidores.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.domain.entities.explanation import Explanation, ExplanationReason
from app.domain.entities.rule_result import RuleResult
from app.domain.entities.scoring_result import ScoringResult
from app.domain.services.explainer import Explainer
from app.domain.services.rules import (
    RULE_ATYPICAL_AMOUNT,
    RULE_GEO_IMPOSSIBLE,
    RULE_RISKY_MERCHANT,
    RULE_VELOCITY,
)
from app.domain.value_objects.rule_catalog import rule_description, rule_title


def _detail_velocity(o: dict[str, Any]) -> str:
    return (
        f"{o.get('count_in_window', '?')} transacciones en "
        f"{o.get('window_minutes', '?')} min "
        f"(límite {o.get('limit', '?')})."
    )


def _detail_atypical_amount(o: dict[str, Any]) -> str:
    base = "el promedio de la cuenta" if o.get("basis") == "account_average" else "el tope absoluto"
    return (
        f"Monto {o.get('amount', '?')} supera el umbral "
        f"{o.get('limit', '?')} basado en {base}."
    )


def _detail_geo_impossible(o: dict[str, Any]) -> str:
    return (
        f"Desplazamiento de {o.get('distance_km', '?')} km en "
        f"{o.get('minutes_since_last', '?')} min ⇒ velocidad implícita "
        f"{o.get('implied_speed_kmh', '?')} km/h "
        f"(máx {o.get('max_speed_kmh', '?')} km/h)."
    )


def _detail_risky_merchant(o: dict[str, Any]) -> str:
    return f"Comercio en categoría de riesgo '{o.get('merchant_category', '?')}'."


# rule_id -> función que arma la frase de detalle desde los valores observados.
_DETAIL_BUILDERS = {
    RULE_VELOCITY: _detail_velocity,
    RULE_ATYPICAL_AMOUNT: _detail_atypical_amount,
    RULE_GEO_IMPOSSIBLE: _detail_geo_impossible,
    RULE_RISKY_MERCHANT: _detail_risky_merchant,
}


def _detail_for(rule: RuleResult) -> str:
    builder = _DETAIL_BUILDERS.get(rule.rule_id)
    if builder is None:
        return rule_description(rule.rule_id)
    return builder(rule.observed)


class RuleBasedExplainer(Explainer):
    """Explicador basado en el catálogo de reglas y la evidencia observada."""

    def explain(self, result: ScoringResult) -> Explanation:
        reasons = [
            ExplanationReason(
                rule_id=rule.rule_id,
                title=rule_title(rule.rule_id),
                description=rule_description(rule.rule_id),
                detail=_detail_for(rule),
                points=rule.points,
                observed=dict(rule.observed),
            )
            for rule in result.triggered_rules
        ]
        return Explanation(
            transaction_id=result.transaction_id,
            account_id=result.account_id,
            score=result.score,
            threshold=result.threshold,
            is_case=result.is_case,
            summary=_summary(result, reasons),
            reasons=reasons,
            generated_at=datetime.now(timezone.utc),
        )


def _summary(result: ScoringResult, reasons: list[ExplanationReason]) -> str:
    if not result.is_case:
        return (
            f"Sin caso: score {result.score}/{result.threshold} no supera el "
            f"umbral."
        )
    titles = ", ".join(r.title for r in reasons)
    n = len(reasons)
    senal = "señal" if n == 1 else "señales"
    return (
        f"Caso abierto: score {result.score}/{result.threshold}. "
        f"{n} {senal}: {titles}."
    )
