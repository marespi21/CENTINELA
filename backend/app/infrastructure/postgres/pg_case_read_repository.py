"""Lectura de casos sobre PostgreSQL (Semana 3, módulo Juan José).

Resuelve un caso por su identificador con su explicación (JSONB persistido de
forma append-only) y su traza de auditoría (`auditoria_casos`). El SDK (`psycopg`)
se importa de forma perezosa; en dev/test se usa el adaptador en memoria.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.application.dtos.explanation_dto import explanation_from_dict
from app.domain.repositories.case_read_repository import CaseDetail, CaseReadRepository


def _iso(value: Any) -> Any:
    return value.isoformat() if isinstance(value, datetime) else value


def build_case_detail(
    case_row: tuple[Any, Any, Any, Any, Any],
    explanation_json: dict[str, Any],
    audit_rows: list[dict[str, Any]],
) -> CaseDetail:
    """Filas de PostgreSQL → `CaseDetail` (función pura, testeable sin BD)."""
    case_id, transaction_id, account_id, status, opened_at = case_row
    audit_trail = [
        {
            "accion": row.get("accion"),
            "usuario": row.get("usuario_accion"),
            "fecha": _iso(row.get("fecha_registro")),
        }
        for row in audit_rows
    ]
    return CaseDetail(
        case_id=str(case_id),
        transaction_id=str(transaction_id) if transaction_id else "",
        account_id=str(account_id) if account_id else "",
        status=str(status),
        opened_at=opened_at,
        explanation=explanation_from_dict(explanation_json),
        audit_trail=audit_trail,
    )


class PgCaseReadRepository(CaseReadRepository):
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def get_case(self, case_id: str) -> CaseDetail | None:
        import psycopg

        with psycopg.connect(self._dsn) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.id, c.transaction_id, c.account_id, e.nombre, c.creado_en
                FROM casos c
                JOIN estados e ON e.id = c.estado_id
                WHERE c.id = %s
                """,
                (case_id,),
            )
            case_row = cur.fetchone()
            if case_row is None:
                return None

            cur.execute(
                """
                SELECT explanation FROM caso_explicaciones
                WHERE caso_id = %s ORDER BY creado_en DESC LIMIT 1
                """,
                (case_id,),
            )
            exp = cur.fetchone()
            if exp is None or not exp[0]:
                return None  # caso sin explicación persistida
            explanation_json = exp[0]

            cur.execute(
                """
                SELECT accion, usuario_accion, fecha_registro
                FROM auditoria_casos
                WHERE caso_id = %s ORDER BY fecha_registro ASC
                """,
                (case_id,),
            )
            audit_rows = [
                {"accion": a[0], "usuario_accion": a[1], "fecha_registro": a[2]}
                for a in cur.fetchall()
            ]

        return build_case_detail(case_row, explanation_json, audit_rows)
