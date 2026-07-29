"""Escritura de casos sobre PostgreSQL (Semana 3 y 5).

- `save_opened_case`: crea el caso (`casos`) y persiste su explicación
  (`caso_explicaciones`, JSONB append-only) en una sola transacción (Semana 3).
- `assign_case` / `resolve_case`: acciones del analista (Semana 5). Escriben en
  `asignaciones` / `resoluciones` y cambian el estado del caso; los triggers de
  la BD generan la auditoría inmutable. Se fija el usuario de aplicación con
  `SET LOCAL app.current_user` para que la auditoría capture al actor real.

El SDK (`psycopg`) se importa de forma perezosa.
"""

from __future__ import annotations

from app.application.dtos.explanation_dto import serialize_explanation
from app.domain.entities.opened_case import OpenedCase
from app.domain.exceptions.case_exceptions import CaseNotFoundError
from app.domain.repositories.case_write_repository import CaseWriteRepository

_APP_USER = "svc-mensajeria"

# Estados definidos en scripts/init-cases-db.sql.
_ESTADO_EN_INVESTIGACION = 2
_ESTADO_RESUELTO = 3


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
            # set_config(...) en vez de SET LOCAL: SET no admite parámetros
            # vinculados y 'current_user' es palabra reservada (rompe el parser).
            cur.execute(
                "SELECT set_config('app.current_user', %s, true)", (_APP_USER,)
            )
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

    def assign_case(self, case_id: str, *, assignee_id: str, actor: str) -> None:
        import psycopg

        with psycopg.connect(self._dsn) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.current_user', %s, true)", (actor,))
            self._ensure_exists(cur, case_id)
            cur.execute(
                "INSERT INTO asignaciones (caso_id, usuario_id) VALUES (%s, %s)",
                (case_id, assignee_id),
            )
            cur.execute(
                "UPDATE casos SET estado_id = %s WHERE id = %s",
                (_ESTADO_EN_INVESTIGACION, case_id),
            )

    def resolve_case(
        self, case_id: str, *, resolution: str, note: str | None, actor: str
    ) -> None:
        import psycopg

        detalle = resolution if not note else f"{resolution} - {note}"
        with psycopg.connect(self._dsn) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.current_user', %s, true)", (actor,))
            self._ensure_exists(cur, case_id)
            cur.execute(
                """
                INSERT INTO resoluciones (caso_id, detalle) VALUES (%s, %s)
                ON CONFLICT (caso_id)
                DO UPDATE SET detalle = EXCLUDED.detalle, resuelto_en = CURRENT_TIMESTAMP
                """,
                (case_id, detalle),
            )
            cur.execute(
                "UPDATE casos SET estado_id = %s WHERE id = %s",
                (_ESTADO_RESUELTO, case_id),
            )

    @staticmethod
    def _ensure_exists(cur, case_id: str) -> None:
        cur.execute("SELECT 1 FROM casos WHERE id = %s", (case_id,))
        if cur.fetchone() is None:
            raise CaseNotFoundError(case_id)
