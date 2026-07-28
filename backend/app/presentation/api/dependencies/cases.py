"""Composition root de la gestión de casos (Semana 3 y 5, módulo Juan José).

Con la base de casos configurada (`CASES_DB_DSN`) → adaptadores PostgreSQL;
sin configuración → en memoria (dev/test). La API depende solo de los puertos.

En modo memoria, la escritura comparte la MISMA instancia de lectura (cacheada)
para que las acciones del analista (asignar/resolver) se reflejen al listar y al
consultar el caso.
"""

from __future__ import annotations

from functools import lru_cache

from app.domain.repositories.case_document_repository import CaseDocumentRepository
from app.domain.repositories.case_read_repository import CaseReadRepository
from app.domain.repositories.case_write_repository import CaseWriteRepository
from app.infrastructure.config.settings import settings
from app.infrastructure.repositories.in_memory_case_document_repository import (
    InMemoryCaseDocumentRepository,
)
from app.infrastructure.repositories.in_memory_case_read_repository import (
    InMemoryCaseReadRepository,
)


@lru_cache(maxsize=1)
def get_case_read_repository() -> CaseReadRepository:
    if settings.cases_db_configured:
        from app.infrastructure.postgres.pg_case_read_repository import (
            PgCaseReadRepository,
        )

        return PgCaseReadRepository(dsn=settings.cases_db_dsn)
    return InMemoryCaseReadRepository()


@lru_cache(maxsize=1)
def get_case_write_repository() -> CaseWriteRepository:
    if settings.cases_db_configured:
        from app.infrastructure.postgres.pg_case_write_repository import (
            PgCaseWriteRepository,
        )

        return PgCaseWriteRepository(dsn=settings.cases_db_dsn)

    from app.infrastructure.repositories.in_memory_case_write_repository import (
        InMemoryCaseWriteRepository,
    )

    read = get_case_read_repository()
    if isinstance(read, InMemoryCaseReadRepository):
        return InMemoryCaseWriteRepository(read_repository=read)
    return InMemoryCaseWriteRepository()


@lru_cache(maxsize=1)
def get_case_document_repository() -> CaseDocumentRepository:
    if settings.cases_db_configured:
        from app.infrastructure.postgres.pg_case_document_repository import (
            PgCaseDocumentRepository,
        )

        return PgCaseDocumentRepository(dsn=settings.cases_db_dsn)
    return InMemoryCaseDocumentRepository()
