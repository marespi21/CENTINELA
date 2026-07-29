"""Motor de scoring de fraude — función serverless (Azure Functions v2).

Se activa ÚNICAMENTE por el evento de transacción (mensaje en la cola
`transactions`). No expone HTTP ni es invocada por la API: su disparador es la
cola. La lógica vive en el caso de uso `ScoreTransactionUseCase`; aquí solo se
hace el binding del trigger.

Desde el Sprint 6 (Fase 1) la composición de dependencias vive en
`app/presentation/worker/composition.py`, compartida con el worker
contenedorizado: ambos despliegues cablean las mismas dependencias. Este archivo
se mantiene operativo a propósito — es el punto de retorno del checkpoint
`pre-sprint6-funcional` si el despliegue en contenedores falla.

Ejecutar localmente:  func start   (requiere Azure Functions Core Tools)
"""
from __future__ import annotations

import logging

import azure.functions as func

from app.application.dtos.scoring_dto import transaction_from_event
from app.presentation.worker.composition import (
    build_persist_case_use_case,
    build_score_use_case,
)

app = func.FunctionApp()


@app.function_name(name="score_transaction")
@app.queue_trigger(
    arg_name="msg",
    queue_name="transactions",
    connection="AzureWebJobsStorage",
)
def score_transaction(msg: func.QueueMessage) -> None:
    """Handler del evento: parsea la transacción y ejecuta el scoring."""
    transaction = transaction_from_event(msg.get_body().decode("utf-8"))
    result = build_score_use_case().execute(transaction)
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
