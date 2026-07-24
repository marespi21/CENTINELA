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
from app.application.use_cases.score_transaction import ScoreTransactionUseCase
from app.domain.repositories.case_queue import CaseQueue
from app.infrastructure.config.settings import settings
from app.infrastructure.messaging.in_memory_case_queue import InMemoryCaseQueue
from app.infrastructure.repositories.in_memory_score_repository import (
    InMemoryScoreRepository,
)
from app.infrastructure.repositories.in_memory_transaction_history_repository import (
    InMemoryTransactionHistoryRepository,
)

app = func.FunctionApp()


def _azure_configured() -> bool:
    return bool(settings.storage_connection_string or settings.storage_account)


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

    Hoy: historial/scores en memoria; cola de casos según settings
    (Azure Queue durable si hay Storage). Sin tocar el caso de uso ni el
    motor de reglas. La config (incluido el umbral) se toma de
    `settings.scoring_config`.
    """
    return ScoreTransactionUseCase(
        history_repository=InMemoryTransactionHistoryRepository(),
        score_repository=InMemoryScoreRepository(),
        case_queue=build_case_queue(),
        config=settings.scoring_config,
    )


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
