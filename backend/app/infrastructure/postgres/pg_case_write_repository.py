"""Escritura de casos sobre PostgreSQL (Semana 3).

Crea el caso (`casos`) y persiste su explicación (`caso_explicaciones`, JSONB
append-only) en una sola transacción, fijando el usuario de aplicación para la
auditoría (`SET LOCAL app.current_user`). El SDK (`psycopg`) se importa perezoso.
"""

from __future__ import annotations

from app.application.dtos.explanation_dto import serialize_explanation
from app.domain.entities.opened_case import OpenedCase
from app.domain.repositories.case_write_repository import CaseWriteRepository

_APP_USER = "svc-mensajeria"


class PgCaseWriteRepository(CaseWriteRepository):
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def save_opened_case(self, case: OpenedCase) -> str:
        import psycopg
        from psycopg.types.json import Jsonb

        explanation_json = serialize_explanation(case.explanation)
        titulo = f"Fraude potencial - cuenta {case.account_id}"

        with psycopg.connect(self._dsn) as conn, conn.cursor() as cur:
            # Usuario de aplicación para la auditoría inmutable.
            cur.execute("SET LOCAL app.current_user = %s", (_APP_USER,))
            cur.execute(
                """
                INSERT INTO casos (titulo, descripcion, estado_id, transaction_id, account_id)
                VALUES (%s, %s, 1, %s, %s)
                RETURNING id
                """,
                (titulo, case.explanation.summary, case.transaction_id, case.account_id),
            )
            case_id = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO caso_explicaciones
                    (caso_id, transaction_id, account_id, score, threshold,
                     is_case, summary, explanation, generado_en)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    case_id,
                    case.transaction_id,
                    case.account_id,
                    case.score,
                    case.threshold,
                    case.explanation.is_case,
                    case.explanation.summary,
                    Jsonb(explanation_json),
                    case.explanation.generated_at,
                ),
            )
        return str(case_id)
