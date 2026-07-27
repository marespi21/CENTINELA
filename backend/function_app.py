"""Motor de scoring de fraude — función serverless (Azure Functions v2).

Se activa ÚNICAMENTE por el evento de transacción (mensaje en la cola
`transactions`). No expone HTTP ni es invocada por la API: su disparador es la
cola. La lógica vive en el caso de uso `ScoreTransactionUseCase`; aquí solo se
hace el binding del trigger y la composición de dependencias.

Ejecutar localmente:  func start   (requiere Azure Functions Core Tools)
"""
from __future__ import annotations

import logging
from functools import lru_cache

import azure.functions as func

from app.application.dtos.scoring_dto import transaction_from_event
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

app = func.FunctionApp()


def _azure_configured() -> bool:
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
    """Composition root de la persistencia de scores (módulo Jorge).

    Con Cosmos configurado → almacén NoSQL; sin configuración → memoria.
    """
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
    if _azure_configured():
        from app.infrastructure.azure.case_queue import AzureCaseQueue

        return AzureCaseQueue(
            queue_name=settings.cases_queue,
            connection_string=settings.storage_connection_string or None,
            account_url=settings.queue_endpoint or None,
        )
    return InMemoryCaseQueue()


@lru_cache(maxsize=1)
def build_use_case() -> ScoreTransactionUseCase:
    """Composition root de la función.

    Selecciona los adaptadores reales cuando la configuración está presente:
    Cosmos DB para historial y scores, y Azure Queue durable para casos; cae a
    los adaptadores en memoria en dev/test. Integra el explicador para adjuntar
    la explicación legible al caso publicado. No se toca el caso de uso ni el
    motor de reglas. La config (incluido el umbral) se lee de app settings.
    """
    return ScoreTransactionUseCase(
        history_repository=build_history_repository(),
        score_repository=build_score_repository(),
        case_queue=build_case_queue(),
        config=settings.scoring_config,
        explainer=RuleBasedExplainer(),
    )


def build_case_write_repository() -> CaseWriteRepository:
    """Composition root de la escritura de casos (módulo Camila/Juan José).

    Con la base de casos configurada → PostgreSQL; sin configuración → memoria.
    """
    if settings.cases_db_configured:
        from app.infrastructure.postgres.pg_case_write_repository import (
            PgCaseWriteRepository,
        )

        return PgCaseWriteRepository(dsn=settings.cases_db_dsn)
    return InMemoryCaseWriteRepository()


@lru_cache(maxsize=1)
def build_persist_case_use_case() -> PersistOpenedCaseUseCase:
    """Composition root del consumidor de la cola `cases` (módulo Camila)."""
    return PersistOpenedCaseUseCase(build_case_write_repository())


@app.function_name(name="score_transaction")
@app.queue_trigger(
    arg_name="msg",
    queue_name="transactions",
    connection="AzureWebJobsStorage",
)
def score_transaction(msg: func.QueueMessage) -> None:
    """Handler del evento: parsea la transacción y ejecuta el scoring."""
    transaction = transaction_from_event(msg.get_body().decode("utf-8"))
    result = build_use_case().execute(transaction)
    logging.info(
        "scored transaction=%s account=%s score=%s threshold=%s case=%s rules=%s",
        result.transaction_id,
        result.account_id,
        result.score,
        result.threshold,
        result.is_case,
        [r.rule_id for r in result.triggered_rules],
    )


@app.function_name(name="persist_case")
@app.queue_trigger(
    arg_name="msg",
    queue_name="cases",
    connection="AzureWebJobsStorage",
)
def persist_case(msg: func.QueueMessage) -> None:
    """Consumidor de la cola durable `cases`: persiste el caso y su explicación.

    La cola garantiza entrega: si esta función está caída, el mensaje permanece
    hasta procesarse (cero pérdida de casos).
    """
    case_id = build_persist_case_use_case().execute(msg.get_body().decode("utf-8"))
    logging.info("persisted case=%s", case_id)
