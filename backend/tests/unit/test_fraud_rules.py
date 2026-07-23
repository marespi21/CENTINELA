from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from app.domain.entities.transaction import Transaction
from app.domain.services.rules import (
    RULE_ATYPICAL_AMOUNT,
    RULE_GEO_IMPOSSIBLE,
    RULE_RISKY_MERCHANT,
    RULE_VELOCITY,
    evaluate_atypical_amount,
    evaluate_geo_impossible,
    evaluate_risky_merchant,
    evaluate_velocity,
)
from app.domain.value_objects.scoring_config import ScoringConfig

BOGOTA = (Decimal("4.7110"), Decimal("-74.0721"))
TOKYO = (Decimal("35.6762"), Decimal("139.6503"))
NOW = datetime(2026, 7, 23, 12, 0, 0, tzinfo=timezone.utc)


def _tx(
    *,
    account_id: str = "acc-001",
    amount: str = "100",
    category: str = "restaurants",
    minutes_ago: int = 0,
    coords: tuple[Decimal, Decimal] = BOGOTA,
) -> Transaction:
    lat, lon = coords
    return Transaction(
        transaction_id=uuid4(),
        account_id=account_id,
        amount=Decimal(amount),
        currency="COP",
        merchant_id="mer-1",
        merchant_category=category,
        timestamp=NOW - timedelta(minutes=minutes_ago),
        latitude=lat,
        longitude=lon,
    )


CONFIG = ScoringConfig(
    velocity_max_tx=5,
    velocity_window_minutes=10,
    amount_factor=Decimal("3.0"),
    amount_min_history=3,
    amount_absolute_cap=Decimal("500"),
    geo_max_speed_kmh=Decimal("900"),
    risky_categories=frozenset({"crypto", "gambling"}),
)


# --- Regla 1: velocidad ------------------------------------------------------
def test_velocity_triggers_with_many_tx_in_window() -> None:
    current = _tx()
    history = [_tx(minutes_ago=m) for m in (1, 2, 3, 8)]  # 4 previas + actual = 5
    result = evaluate_velocity(current, history, CONFIG)
    assert result.rule_id == RULE_VELOCITY
    assert result.triggered is True
    assert result.observed["count_in_window"] == 5


def test_velocity_does_not_trigger_outside_window() -> None:
    current = _tx()
    history = [_tx(minutes_ago=m) for m in (1, 2, 30, 40)]  # solo 2 dentro de 10 min
    result = evaluate_velocity(current, history, CONFIG)
    assert result.triggered is False
    assert result.points == 0


# --- Regla 2: monto atípico --------------------------------------------------
def test_atypical_amount_triggers_above_account_average() -> None:
    current = _tx(amount="1000")
    history = [_tx(amount="100", minutes_ago=m) for m in (10, 20, 30)]  # avg=100, limite=300
    result = evaluate_atypical_amount(current, history, CONFIG)
    assert result.rule_id == RULE_ATYPICAL_AMOUNT
    assert result.triggered is True
    assert result.observed["account_average"] == 100.0
    assert result.observed["limit"] == 300.0


def test_atypical_amount_uses_absolute_cap_without_history() -> None:
    current = _tx(amount="600")  # cap=500, sin historial suficiente
    result = evaluate_atypical_amount(current, [], CONFIG)
    assert result.triggered is True
    assert result.observed["basis"] == "absolute_cap"


def test_atypical_amount_does_not_trigger_when_normal() -> None:
    current = _tx(amount="200")
    history = [_tx(amount="100", minutes_ago=m) for m in (10, 20, 30)]  # limite=300
    assert evaluate_atypical_amount(current, history, CONFIG).triggered is False


# --- Regla 3: geo-imposible --------------------------------------------------
def test_geo_impossible_triggers_on_impossible_speed() -> None:
    current = _tx(coords=TOKYO)
    history = [_tx(coords=BOGOTA, minutes_ago=10)]  # ~14.000 km en 10 min
    result = evaluate_geo_impossible(current, history, CONFIG)
    assert result.rule_id == RULE_GEO_IMPOSSIBLE
    assert result.triggered is True
    assert result.observed["implied_speed_kmh"] != "infinita"
    assert result.observed["distance_km"] > 900


def test_geo_impossible_does_not_trigger_for_feasible_move() -> None:
    current = _tx(coords=(Decimal("4.72"), Decimal("-74.06")))
    history = [_tx(coords=BOGOTA, minutes_ago=60)]  # ~1.5 km en 60 min
    assert evaluate_geo_impossible(current, history, CONFIG).triggered is False


def test_geo_impossible_does_not_trigger_without_history() -> None:
    assert evaluate_geo_impossible(_tx(), [], CONFIG).triggered is False


# --- Regla 4: comercio de riesgo ---------------------------------------------
def test_risky_merchant_triggers_for_risky_category() -> None:
    result = evaluate_risky_merchant(_tx(category="crypto"), [], CONFIG)
    assert result.rule_id == RULE_RISKY_MERCHANT
    assert result.triggered is True
    assert result.observed["merchant_category"] == "crypto"


def test_risky_merchant_does_not_trigger_for_normal_category() -> None:
    assert evaluate_risky_merchant(_tx(category="restaurants"), [], CONFIG).triggered is False
