from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from app.domain.entities.transaction import Transaction
from app.domain.services.rules import RULE_GEO_IMPOSSIBLE, RULE_RISKY_MERCHANT
from app.domain.services.scoring_engine import ScoringEngine
from app.domain.value_objects.scoring_config import ScoringConfig

NOW = datetime(2026, 7, 23, 12, 0, 0, tzinfo=timezone.utc)
BOGOTA = (Decimal("4.7110"), Decimal("-74.0721"))
TOKYO = (Decimal("35.6762"), Decimal("139.6503"))

CONFIG = ScoringConfig(
    threshold=50,
    weight_geo_impossible=45,
    weight_risky_merchant=20,
    risky_categories=frozenset({"crypto"}),
)


def _tx(*, category="restaurants", coords=BOGOTA, minutes_ago=0) -> Transaction:
    lat, lon = coords
    return Transaction(
        transaction_id=uuid4(),
        account_id="acc-001",
        amount=Decimal("100"),
        currency="COP",
        merchant_id="mer-1",
        merchant_category=category,
        timestamp=NOW - timedelta(minutes=minutes_ago),
        latitude=lat,
        longitude=lon,
    )


def test_engine_sums_points_and_opens_case_when_two_rules_fire() -> None:
    engine = ScoringEngine()
    # geo-imposible (45) + comercio de riesgo (20) = 65 >= 50
    current = _tx(category="crypto", coords=TOKYO)
    history = [_tx(coords=BOGOTA, minutes_ago=10)]

    result = engine.score(current, history, CONFIG)

    assert result.score == 65
    assert result.threshold == 50
    assert result.is_case is True
    fired = {r.rule_id for r in result.triggered_rules}
    assert fired == {RULE_GEO_IMPOSSIBLE, RULE_RISKY_MERCHANT}


def test_engine_does_not_open_case_below_threshold() -> None:
    engine = ScoringEngine()
    # solo comercio de riesgo (20) < 50
    result = engine.score(_tx(category="crypto"), [], CONFIG)
    assert result.score == 20
    assert result.is_case is False


def test_engine_persists_concrete_observed_values_per_rule() -> None:
    engine = ScoringEngine()
    current = _tx(category="crypto", coords=TOKYO)
    history = [_tx(coords=BOGOTA, minutes_ago=10)]

    result = engine.score(current, history, CONFIG)

    geo = next(r for r in result.triggered_rules if r.rule_id == RULE_GEO_IMPOSSIBLE)
    # No solo el id: guarda los valores que la activaron.
    assert "distance_km" in geo.observed
    assert "implied_speed_kmh" in geo.observed
    assert geo.observed["max_speed_kmh"] == 900.0
