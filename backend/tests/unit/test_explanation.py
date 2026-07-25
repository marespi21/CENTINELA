"""Tests del contrato del explicador (Semana 3).

Verifican que el explicador de referencia produce una explicación coherente y
que la serialización cumple el contrato JSON compartido (camelCase).
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.application.dtos.explanation_dto import serialize_explanation
from app.application.services.rule_based_explainer import RuleBasedExplainer
from app.domain.entities.rule_result import RuleResult
from app.domain.entities.scoring_result import ScoringResult
from app.domain.services.rules import RULE_ATYPICAL_AMOUNT, RULE_VELOCITY

_TX_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


def _case_result() -> ScoringResult:
    """Resultado que abre caso: velocidad + monto atípico (55 ≥ 50)."""
    return ScoringResult(
        transaction_id=_TX_ID,
        account_id="acc-001",
        score=55,
        threshold=50,
        rule_results=[
            RuleResult(
                rule_id=RULE_VELOCITY,
                triggered=True,
                points=25,
                observed={"count_in_window": 6, "window_minutes": 10, "limit": 5},
            ),
            RuleResult(
                rule_id=RULE_ATYPICAL_AMOUNT,
                triggered=True,
                points=30,
                observed={"amount": 900000.0, "limit": 300000.0, "basis": "account_average"},
            ),
        ],
        is_case=True,
        scored_at=datetime(2026, 7, 25, 12, 0, tzinfo=timezone.utc),
    )


class TestRuleBasedExplainer:
    def test_explains_only_triggered_rules(self) -> None:
        result = ScoringResult(
            transaction_id=_TX_ID,
            account_id="acc-001",
            score=25,
            threshold=50,
            rule_results=[
                RuleResult(rule_id=RULE_VELOCITY, triggered=True, points=25,
                           observed={"count_in_window": 6, "window_minutes": 10, "limit": 5}),
                RuleResult(rule_id=RULE_ATYPICAL_AMOUNT, triggered=False, points=0, observed={}),
            ],
            is_case=False,
            scored_at=datetime(2026, 7, 25, 12, 0, tzinfo=timezone.utc),
        )
        explanation = RuleBasedExplainer().explain(result)
        assert len(explanation.reasons) == 1
        assert explanation.reasons[0].rule_id == RULE_VELOCITY
        assert not explanation.is_case
        assert "Sin caso" in explanation.summary

    def test_case_summary_lists_signals(self) -> None:
        explanation = RuleBasedExplainer().explain(_case_result())
        assert explanation.is_case
        assert explanation.score == 55
        assert len(explanation.reasons) == 2
        # El título humano viene del catálogo, no el rule_id crudo.
        titles = {r.title for r in explanation.reasons}
        assert "Velocidad de transacciones inusual" in titles
        assert "Monto atípico" in titles
        assert "Caso abierto" in explanation.summary

    def test_reason_detail_uses_observed_evidence(self) -> None:
        explanation = RuleBasedExplainer().explain(_case_result())
        velocity = next(r for r in explanation.reasons if r.rule_id == RULE_VELOCITY)
        assert "6 transacciones en 10 min" in velocity.detail


class TestExplanationSerialization:
    def test_serialize_matches_camelcase_contract(self) -> None:
        explanation = RuleBasedExplainer().explain(_case_result())
        payload = serialize_explanation(explanation)

        assert payload["transactionId"] == str(_TX_ID)
        assert payload["accountId"] == "acc-001"
        assert payload["score"] == 55
        assert payload["threshold"] == 50
        assert payload["isCase"] is True
        assert payload["generatedAt"].endswith("Z")
        assert isinstance(payload["reasons"], list) and len(payload["reasons"]) == 2

        reason = payload["reasons"][0]
        assert set(reason.keys()) == {
            "ruleId", "title", "description", "detail", "points", "observed",
        }
