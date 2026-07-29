"""Composition root del motor de scoring — compartido por la Function y el contenedor.

Antes vivía dentro de `function_app.py`. Se extrae aquí para que el worker
contenedorizado (Sprint 6, Fase 1) y la Azure Function ejecuten **exactamente**
la misma composición de dependencias: si el contenedor puntúa distinto que la
Function, no será por culpa del cableado. `function_app.py` se conserva intacto
en su comportamiento y sigue siendo el punto de retorno del checkpoint.

Selección de adaptadores (idéntica a la anterior):
- Cosmos configurado  → historial y scores en Cosmos DB; si no, memoria.
- Storage configurado → cola `cases` durable en Azure Queue; si no, memoria.
- Base de casos configurada → PostgreSQL; si no, memoria.
"""

from __future__ import annotations

from functools import lru_cache

from app.application.services.rule_based_explainer import RuleBasedExplainer
from app.application.use_cases.persist_opened_case import PersistOpenedCaseUseCase
from app.application.use_cases.score_transaction import ScoreTransactionUseCase
from app.domain.repositories.case_queue import CaseQueue
from app.domain.repositories.case_write_repository import CaseWriteRepository
from app.domain.repositories.score_repository import ScoreRepository
from app.domain.repositories.transaction_history_repository import (
    TransactionHistoryRepository,
)
from app.infrastructure.config.settings import settings
from app.infrastructure.messaging.in_memory_case_queue import InMemoryCaseQueue
from app.infrastructure.repositories.in_memory_case_write_repository import (
    InMemoryCaseWriteRepository,
)
from app.infrastructure.repositories.in_memory_score_repository import (
    InMemoryScoreRepository,
)
from app.infrastructure.repositories.in_memory_transaction_history_repository import (
    InMemoryTransactionHistoryRepository,
)


def azure_configured() -> bool:
    return bool(settings.storage_connection_string or settings.storage_account)


def build_history_repository() -> TransactionHistoryRepository:
    """Composition root del historial (módulo Jorge).

    Con Cosmos configurado → almacén NoSQL; sin configuración → memoria.
    """
    if settings.cosmos_configured:
        from app.infrastructure.azure.cosmos_transaction_history_repository import (
            CosmosTransactionHistoryRepository,
        )

        return CosmosTransactionHistoryRepository(
            endpoint=settings.cosmos_endpoint,
            database=settings.cosmos_database,
            container=settings.cosmos_container,
            key=settings.cosmos_key or None,
        )
    return InMemoryTransactionHistoryRepository()


def build_score_repository() -> ScoreRepository:
    """Composition root de la persistencia de scores (módulo Jorge)."""
    if settings.cosmos_configured:
        from app.infrastructure.azure.cosmos_score_repository import (
            CosmosScoreRepository,
        )

        return CosmosScoreRepository(
            endpoint=settings.cosmos_endpoint,
            database=settings.cosmos_database,
            container=settings.cosmos_container,
            key=settings.cosmos_key or None,
        )
    return InMemoryScoreRepository()


def build_case_queue() -> CaseQueue:
    """Composition root de la cola de casos (módulo Camila).

    Con Storage configurado → Azure Queue durable (`cases`).
    Sin configuración → memoria (dev/test).
    """
    if azure_configured():
        from app.infrastructure.azure.case_queue import AzureCaseQueue

        return AzureCaseQueue(
            queue_name=settings.cases_queue,
            connection_string=settings.storage_connection_string or None,
            account_url=settings.queue_endpoint or None,
        )
    return InMemoryCaseQueue()


def build_case_write_repository() -> CaseWriteRepository:
    """Composition root de la escritura de casos (módulo Camila/Juan José)."""
    if settings.cases_db_configured:
        from app.infrastructure.postgres.pg_case_write_repository import (
            PgCaseWriteRepository,
        )

        return PgCaseWriteRepository(dsn=settings.cases_db_dsn)
    return InMemoryCaseWriteRepository()


@lru_cache(maxsize=1)
def build_score_use_case() -> ScoreTransactionUseCase:
    """Caso de uso de scoring, con explicación adjunta al caso publicado.

    La config (incluido el umbral) se lee de variables de entorno: cambiar el
    umbral no requiere reconstruir la imagen, solo reiniciar la revisión.
    """
    return ScoreTransactionUseCase(
        history_repository=build_history_repository(),
        score_repository=build_score_repository(),
        case_queue=build_case_queue(),
        config=settings.scoring_config,
        explainer=RuleBasedExplainer(),
    )


@lru_cache(maxsize=1)
def build_persist_case_use_case() -> PersistOpenedCaseUseCase:
    """Consumidor de la cola `cases` (módulo Camila)."""
    return PersistOpenedCaseUseCase(build_case_write_repository())
