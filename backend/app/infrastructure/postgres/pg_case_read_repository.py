"""Lectura de casos sobre PostgreSQL (Semana 3 y 5, módulo Juan José).

Resuelve un caso por su identificador (con su explicación JSONB append-only, su
asignación vigente y su traza de auditoría) y LISTA los casos con filtros y
paginación para la bandeja. El SDK (`psycopg`) se importa de forma perezosa; en
dev/test se usa el adaptador en memoria.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.application.dtos.explanation_dto import explanation_from_dict
from app.domain.repositories.case_read_repository import (
    CaseDetail,
    CaseListQuery,
    CasePage,
    CaseReadRepository,
    CaseSummary,
)


def _iso(value: Any) -> Any:
    return value.isoformat() if isinstance(value, datetime) else value


def build_case_detail(
    case_row: tuple[Any, Any, Any, Any, Any],
    explanation_json: dict[str, Any],
    audit_rows: list[dict[str, Any]],
    assignee: str | None = None,
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
        assignee=assignee,
    )


def build_case_summary(row: tuple[Any, ...]) -> CaseSummary:
    """Fila de la consulta de bandeja → `CaseSummary` (función pura)."""
    return CaseSummary(
        case_id=str(row[0]),
        transaction_id=str(row[1]) if row[1] else "",
        account_id=str(row[2]) if row[2] else "",
        status=str(row[3]),
        opened_at=row[4],
        score=int(row[5]),
        is_case=bool(row[6]),
        summary=str(row[7]),
        assignee=str(row[8]) if row[8] else None,
    )


_LIST_FROM = """
FROM casos c
JOIN estados e ON e.id = c.estado_id
LEFT JOIN LATERAL (
    SELECT score, is_case, summary
    FROM caso_explicaciones
    WHERE caso_id = c.id
    ORDER BY creado_en DESC
    LIMIT 1
) ce ON TRUE
LEFT JOIN LATERAL (
    SELECT usuario_id
    FROM asignaciones
    WHERE caso_id = c.id
    ORDER BY asignado_en DESC
    LIMIT 1
) a ON TRUE
"""

# Los parámetros se castean (::text / ::timestamptz) para que PostgreSQL infiera
# el tipo cuando el filtro es NULL; sin el cast lanza "could not determine data
# type of parameter" en la comparación `%(param)s IS NULL`.
_LIST_WHERE = """
WHERE (%(status)s::text IS NULL OR e.nombre = %(status)s::text)
  AND (%(assigned_to)s::text IS NULL OR a.usuario_id::text = %(assigned_to)s::text)
  AND (%(date_from)s::timestamptz IS NULL OR c.creado_en >= %(date_from)s::timestamptz)
  AND (%(date_to)s::timestamptz IS NULL OR c.creado_en <= %(date_to)s::timestamptz)
"""


def build_list_query(query: CaseListQuery) -> tuple[str, str, dict[str, Any]]:
    """`CaseListQuery` → (SQL de página, SQL de conteo, parámetros). Función pura."""
    list_sql = (
        "SELECT c.id, c.transaction_id, c.account_id, e.nombre, c.creado_en, "
        "COALESCE(ce.score, 0), COALESCE(ce.is_case, FALSE), COALESCE(ce.summary, '') , "
        "a.usuario_id"
        f"{_LIST_FROM}{_LIST_WHERE}"
        "ORDER BY c.creado_en DESC\n"
        "LIMIT %(limit)s OFFSET %(offset)s"
    )
    count_sql = f"SELECT COUNT(*){_LIST_FROM}{_LIST_WHERE}"
    params = {
        "status": query.status,
        "assigned_to": query.assigned_to,
        "date_from": query.date_from,
        "date_to": query.date_to,
        "limit": query.page_size,
        "offset": query.offset,
    }
    return list_sql, count_sql, params


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
                SELECT usuario_id FROM asignaciones
                WHERE caso_id = %s ORDER BY asignado_en DESC LIMIT 1
                """,
                (case_id,),
            )
            assignee_row = cur.fetchone()
            assignee = str(assignee_row[0]) if assignee_row else None

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

        return build_case_detail(case_row, explanation_json, audit_rows, assignee)

    def list_cases(self, query: CaseListQuery) -> CasePage:
        import psycopg

        list_sql, count_sql, params = build_list_query(query)
        with psycopg.connect(self._dsn) as conn, conn.cursor() as cur:
            cur.execute(count_sql, params)
            total = int(cur.fetchone()[0])
            cur.execute(list_sql, params)
            items = [build_case_summary(row) for row in cur.fetchall()]

        return CasePage(
            items=items, total=total, page=query.page, page_size=query.page_size
        )
