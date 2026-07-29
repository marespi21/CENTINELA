"""Motor de scoring como proceso autónomo — entrypoint del contenedor.

Sustituye al disparador de Azure Functions por un bucle explícito de sondeo de
colas. La lógica de negocio no cambia: se reutilizan los mismos casos de uso y
el mismo composition root (`composition.py`) que usa `function_app.py`.

Qué había que reponer al salir de Azure Functions, y cómo se hace aquí:

- **Reintento**: un mensaje que falla NO se borra; al expirar su *visibility
  timeout* vuelve a la cola y se reintenta.
- **Poison queue**: superado `WORKER_MAX_DEQUEUE_COUNT`, el mensaje se aparta a
  `<cola>-poison` para que un mensaje corrupto no bloquee el flujo.
- **Escalado**: lo aporta KEDA en Container Apps (scaler `azure-queue`), que
  mide la longitud de la cola y puede bajar a cero réplicas.
- **Apagado limpio**: se atiende SIGTERM (la señal que envía Container Apps al
  escalar a cero o al desplegar una revisión) para terminar el mensaje en curso
  antes de salir, en vez de morir a mitad de proceso.

Ejecutar:  python -m app.presentation.worker.main
"""

from __future__ import annotations

import logging
import os
import signal
import threading
from collections.abc import Callable
from dataclasses import dataclass

from app.application.dtos.scoring_dto import transaction_from_event
from app.domain.repositories.message_consumer import MessageConsumer, ReceivedMessage
from app.infrastructure.config.settings import settings
from app.infrastructure.observability.telemetry import (
    get_counter,
    get_tracer,
    setup_telemetry,
)
from app.presentation.worker.composition import (
    azure_configured,
    build_persist_case_use_case,
    build_score_use_case,
    build_verify_document_use_case,
)

logger = logging.getLogger(__name__)
tracer = get_tracer("centinela.worker")

_messages_processed = get_counter(
    "centinela.worker",
    "centinela.worker.messages.processed",
    "Mensajes de cola procesados con éxito",
)
_messages_failed = get_counter(
    "centinela.worker",
    "centinela.worker.messages.failed",
    "Mensajes de cola que fallaron y se reintentarán",
)
_messages_dead_lettered = get_counter(
    "centinela.worker",
    "centinela.worker.messages.dead_lettered",
    "Mensajes apartados a la cola poison",
)


@dataclass(frozen=True)
class WorkerConfig:
    """Parámetros del bucle, ajustables por entorno sin reconstruir la imagen."""

    poll_interval_seconds: float = float(os.getenv("WORKER_POLL_INTERVAL", "5"))
    # Debe superar con margen lo que tarda procesar un mensaje: si expira antes,
    # el mensaje se reentregaría y se procesaría dos veces.
    visibility_timeout_seconds: int = int(os.getenv("WORKER_VISIBILITY_TIMEOUT", "60"))
    max_messages: int = int(os.getenv("WORKER_BATCH_SIZE", "16"))
    max_dequeue_count: int = int(os.getenv("WORKER_MAX_DEQUEUE_COUNT", "5"))


class QueuePump:
    """Bombea una cola: recibe, procesa con `handler`, y borra si fue bien."""

    def __init__(
        self,
        name: str,
        consumer: MessageConsumer,
        handler: Callable[[str], None],
        config: WorkerConfig,
    ) -> None:
        self._name = name
        self._consumer = consumer
        self._handler = handler
        self._config = config

    @property
    def name(self) -> str:
        return self._name

    def pump_once(self) -> int:
        """Procesa un lote. Devuelve cuántos mensajes se leyeron (no cuántos fueron bien)."""
        messages = self._consumer.receive(
            max_messages=self._config.max_messages,
            visibility_timeout=self._config.visibility_timeout_seconds,
        )
        for message in messages:
            self._process(message)
        return len(messages)

    def _process(self, message: ReceivedMessage) -> None:
        with tracer.start_as_current_span(f"queue.process {self._name}") as span:
            span.set_attribute("messaging.system", "azure_queue")
            span.set_attribute("messaging.destination.name", self._name)
            span.set_attribute("messaging.message.id", message.message_id)
            span.set_attribute("messaging.azure.delivery_count", message.dequeue_count)
            try:
                self._handler(message.content)
            except Exception as exc:  # noqa: BLE001 - un mensaje malo no tumba el worker
                span.record_exception(exc)
                self._handle_failure(message)
                return
            self._consumer.delete(message)
            _messages_processed.add(1, {"queue": self._name})

    def _handle_failure(self, message: ReceivedMessage) -> None:
        """Aparta el mensaje si ya falló demasiadas veces; si no, lo deja reintentar."""
        if message.dequeue_count >= self._config.max_dequeue_count:
            try:
                self._consumer.dead_letter(message)
                _messages_dead_lettered.add(1, {"queue": self._name})
            except Exception:  # noqa: BLE001 - defensivo
                logger.exception(
                    "no se pudo apartar el mensaje envenenado queue=%s message_id=%s",
                    self._name,
                    message.message_id,
                )
            return
        _messages_failed.add(1, {"queue": self._name})
        logger.exception(
            "fallo procesando queue=%s message_id=%s entrega=%s/%s; se reintentará",
            self._name,
            message.message_id,
            message.dequeue_count,
            self._config.max_dequeue_count,
        )


def run_worker(
    pumps: list[QueuePump],
    shutdown: threading.Event,
    config: WorkerConfig,
) -> None:
    """Bucle principal: sondea todas las colas hasta que se pida el apagado.

    Si ninguna cola tenía trabajo, espera `poll_interval_seconds` — pero la
    espera es interrumpible por SIGTERM, así que el apagado es inmediato.
    """
    logger.info(
        "worker iniciado colas=%s intervalo=%ss lote=%s",
        [pump.name for pump in pumps],
        config.poll_interval_seconds,
        config.max_messages,
    )
    while not shutdown.is_set():
        received = 0
        for pump in pumps:
            if shutdown.is_set():
                break
            try:
                received += pump.pump_once()
            except Exception:  # noqa: BLE001 - fallo de red/servicio: reintentar
                logger.exception("error sondeando la cola %s", pump.name)
        if received == 0:
            shutdown.wait(config.poll_interval_seconds)
    logger.info("worker detenido limpiamente")


def build_pumps(config: WorkerConfig) -> list[QueuePump]:
    """Crea los dos consumidores: scoring (`transactions`) y casos (`cases`)."""
    from app.infrastructure.azure.queue_consumer import AzureQueueConsumer

    def consumer_for(queue_name: str) -> AzureQueueConsumer:
        consumer = AzureQueueConsumer(
            queue_name=queue_name,
            connection_string=settings.storage_connection_string or None,
            account_url=settings.queue_endpoint or None,
        )
        consumer.ensure_queue()
        return consumer

    def handle_transaction(content: str) -> None:
        result = build_score_use_case().execute(transaction_from_event(content))
        logger.info(
            "scored transaction=%s account=%s score=%s threshold=%s case=%s rules=%s",
            result.transaction_id,
            result.account_id,
            result.score,
            result.threshold,
            result.is_case,
            [rule.rule_id for rule in result.triggered_rules],
        )

    def handle_case(content: str) -> None:
        logger.info("persisted case=%s", build_persist_case_use_case().execute(content))

    def handle_document(content: str) -> None:
        verification = build_verify_document_use_case().execute(content)
        if verification is not None:
            logger.info(
                "documento verificado veredicto=%s resumen=%s",
                verification.verdict.value,
                verification.summary,
            )

    return [
        QueuePump(
            settings.transactions_queue, consumer_for(settings.transactions_queue),
            handle_transaction, config,
        ),
        QueuePump(
            settings.cases_queue, consumer_for(settings.cases_queue),
            handle_case, config,
        ),
        # Cola `documents`: existía desde la semana 1 pero nadie la consumía, así
        # que los eventos `document.uploaded` se acumulaban sin procesarse.
        QueuePump(
            settings.documents_queue, consumer_for(settings.documents_queue),
            handle_document, config,
        ),
    ]


def main() -> int:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    setup_telemetry("centinela-worker")

    if not azure_configured():
        logger.error(
            "sin STORAGE_ACCOUNT ni STORAGE_CONNECTION_STRING no hay colas que sondear; "
            "el worker no tiene nada que hacer"
        )
        return 1

    shutdown = threading.Event()

    def request_shutdown(signum: int, _frame: object) -> None:
        logger.info("señal %s recibida; terminando el mensaje en curso", signum)
        shutdown.set()

    signal.signal(signal.SIGTERM, request_shutdown)
    signal.signal(signal.SIGINT, request_shutdown)

    config = WorkerConfig()
    run_worker(build_pumps(config), shutdown, config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
