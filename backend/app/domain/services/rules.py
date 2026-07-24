from __future__ import annotations

import math
from decimal import Decimal

from app.domain.entities.rule_result import RuleResult
from app.domain.entities.transaction import Transaction
from app.domain.value_objects.scoring_config import ScoringConfig

# Identificadores estables de las 4 reglas (se persisten en el detalle).
RULE_VELOCITY = "velocity"
RULE_ATYPICAL_AMOUNT = "atypical_amount"
RULE_GEO_IMPOSSIBLE = "geo_impossible"
RULE_RISKY_MERCHANT = "risky_merchant"


def _haversine_km(lat1: Decimal, lon1: Decimal, lat2: Decimal, lon2: Decimal) -> float:
    """Distancia en km entre dos coordenadas (fórmula de Haversine)."""
    r = 6371.0  # radio terrestre (km)
    phi1, phi2 = math.radians(float(lat1)), math.radians(float(lat2))
    dphi = math.radians(float(lat2) - float(lat1))
    dlambda = math.radians(float(lon2) - float(lon1))
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _recent_history(transaction: Transaction, history: list[Transaction]) -> list[Transaction]:
    """Transacciones anteriores a la actual (timestamp estrictamente menor)."""
    return [t for t in history if t.timestamp < transaction.timestamp]


def evaluate_velocity(
    transaction: Transaction, history: list[Transaction], config: ScoringConfig
) -> RuleResult:
    """Demasiadas transacciones de la cuenta en una ventana corta."""
    window = config.velocity_window_minutes
    prior = _recent_history(transaction, history)
    in_window = [
        t
        for t in prior
        if (transaction.timestamp - t.timestamp).total_seconds() <= window * 60
    ]
    count = len(in_window) + 1  # incluye la transacción actual
    triggered = count >= config.velocity_max_tx
    return RuleResult(
        rule_id=RULE_VELOCITY,
        triggered=triggered,
        points=config.weight_velocity if triggered else 0,
        observed={
            "count_in_window": count,
            "window_minutes": window,
            "limit": config.velocity_max_tx,
        },
    )


def evaluate_atypical_amount(
    transaction: Transaction, history: list[Transaction], config: ScoringConfig
) -> RuleResult:
    """Monto muy por encima de lo habitual de la cuenta."""
    prior = _recent_history(transaction, history)
    if len(prior) >= config.amount_min_history:
        avg = sum((t.amount for t in prior), Decimal(0)) / Decimal(len(prior))
        limit = config.amount_factor * avg
        basis = "account_average"
        observed_basis: dict[str, object] = {
            "account_average": float(round(avg, 2)),
            "factor": float(config.amount_factor),
        }
    else:
        limit = config.amount_absolute_cap
        basis = "absolute_cap"
        observed_basis = {"absolute_cap": float(config.amount_absolute_cap)}

    triggered = transaction.amount > limit
    return RuleResult(
        rule_id=RULE_ATYPICAL_AMOUNT,
        triggered=triggered,
        points=config.weight_atypical_amount if triggered else 0,
        observed={
            "amount": float(transaction.amount),
            "limit": float(round(limit, 2)),
            "basis": basis,
            **observed_basis,
        },
    )


def evaluate_geo_impossible(
    transaction: Transaction, history: list[Transaction], config: ScoringConfig
) -> RuleResult:
    """Desplazamiento físicamente imposible respecto a la transacción anterior."""
    prior = _recent_history(transaction, history)
    if not prior:
        return RuleResult(
            rule_id=RULE_GEO_IMPOSSIBLE,
            triggered=False,
            points=0,
            observed={"reason": "sin transacción previa"},
        )

    last = max(prior, key=lambda t: t.timestamp)
    distance_km = _haversine_km(
        last.latitude, last.longitude, transaction.latitude, transaction.longitude
    )
    minutes = (transaction.timestamp - last.timestamp).total_seconds() / 60
    hours = minutes / 60

    if hours <= 0:
        # Mismo instante en dos lugares distintos ⇒ imposible.
        speed_kmh = float("inf") if distance_km > 0 else 0.0
    else:
        speed_kmh = distance_km / hours

    triggered = speed_kmh > float(config.geo_max_speed_kmh)
    return RuleResult(
        rule_id=RULE_GEO_IMPOSSIBLE,
        triggered=triggered,
        points=config.weight_geo_impossible if triggered else 0,
        observed={
            "distance_km": round(distance_km, 2),
            "minutes_since_last": round(minutes, 2),
            "implied_speed_kmh": (
                round(speed_kmh, 2) if math.isfinite(speed_kmh) else "infinita"
            ),
            "max_speed_kmh": float(config.geo_max_speed_kmh),
            "from": [float(last.latitude), float(last.longitude)],
            "to": [float(transaction.latitude), float(transaction.longitude)],
        },
    )


def evaluate_risky_merchant(
    transaction: Transaction, history: list[Transaction], config: ScoringConfig
) -> RuleResult:
    """Categoría del comercio marcada como de riesgo."""
    category = transaction.merchant_category.strip().lower()
    triggered = category in config.risky_categories
    return RuleResult(
        rule_id=RULE_RISKY_MERCHANT,
        triggered=triggered,
        points=config.weight_risky_merchant if triggered else 0,
        observed={
            "merchant_category": category,
            "risky_categories": sorted(config.risky_categories),
        },
    )


# Orden estable de evaluación de las 4 reglas.
ALL_RULES = (
    evaluate_velocity,
    evaluate_atypical_amount,
    evaluate_geo_impossible,
    evaluate_risky_merchant,
)
