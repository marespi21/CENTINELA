"""Constructores de consulta de la bandeja en PostgreSQL (Semana 5).

Prueban las funciones puras (sin BD) que arman el SQL y mapean filas: filtros +
paginación en `build_list_query`, y el mapeo de fila -> `CaseSummary`.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.domain.repositories.case_read_repository import CaseListQuery
from app.infrastructure.postgres.pg_case_read_repository import (
    build_case_summary,
    build_list_query,
)


def test_build_list_query_has_order_pagination_and_params() -> None:
    query = CaseListQuery(status="Abierto", page=3, page_size=10)

    list_sql, count_sql, params = build_list_query(query)

    assert "ORDER BY c.creado_en DESC" in list_sql
    assert "LIMIT %(limit)s OFFSET %(offset)s" in list_sql
    assert count_sql.startswith("SELECT COUNT(*)")
    assert params["status"] == "Abierto"
    assert params["limit"] == 10
    assert params["offset"] == 20  # (page-1)*page_size


def test_build_list_query_null_filters_when_absent() -> None:
    _, _, params = build_list_query(CaseListQuery())

    assert params["status"] is None
    assert params["assigned_to"] is None
    assert params["date_from"] is None
    assert params["date_to"] is None


def test_build_case_summary_maps_row() -> None:
    opened = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
    row = (
        "case-1",
        "550e8400-e29b-41d4-a716-446655440000",
        "acc-001",
        "Abierto",
        opened,
        55,
        True,
        "Resumen",
        "11111111-1111-1111-1111-111111111111",
    )

    summary = build_case_summary(row)

    assert summary.case_id == "case-1"
    assert summary.account_id == "acc-001"
    assert summary.status == "Abierto"
    assert summary.score == 55
    assert summary.is_case is True
    assert summary.summary == "Resumen"
    assert summary.assignee == "11111111-1111-1111-1111-111111111111"


def test_build_case_summary_handles_null_assignee() -> None:
    row = ("c", "tx", "acc", "Abierto", datetime.now(timezone.utc), 0, False, "", None)

    summary = build_case_summary(row)

    assert summary.assignee is None
    assert summary.is_case is False
