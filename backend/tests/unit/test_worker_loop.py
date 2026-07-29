"""Tests del bucle del worker contenedorizado (Sprint 6, Fase 1).

Al salir de Azure Functions perdimos tres garantías que el host daba gratis:
reintento del mensaje que falla, desvío a la cola *poison* y apagado limpio al
recibir SIGTERM. Aquí se comprueba que la implementación propia las repone —
sin tocar Azure: el consumidor es un doble en memoria.
"""

from __future__ import annotations

import threading

from app.domain.repositories.message_consumer import MessageConsumer, ReceivedMessage
from app.presentation.worker.main import QueuePump, WorkerConfig, run_worker


class FakeConsumer(MessageConsumer):
    """Cola en memoria que imita la semántica de Azure Queue Storage.

    Lo relevante: un mensaje recibido y NO borrado vuelve a entregarse, con el
    contador de entregas incrementado, igual que al expirar el visibility
    timeout real.
    """

    def __init__(self, contents: list[str]) -> None:
        self._pending = [
            ReceivedMessage(
                message_id=f"m{index}",
                pop_receipt=f"r{index}",
                content=content,
                dequeue_count=1,
            )
            for index, content in enumerate(contents)
        ]
        self.deleted: list[str] = []
        self.dead_lettered: list[str] = []

    def receive(self, max_messages: int, visibility_timeout: int) -> list[ReceivedMessage]:
        batch = self._pending[:max_messages]
        self._pending = self._pending[max_messages:]
        return batch

    def delete(self, message: ReceivedMessage) -> None:
        self.deleted.append(message.message_id)

    def dead_letter(self, message: ReceivedMessage) -> None:
        self.dead_lettered.append(message.message_id)
        self.deleted.append(message.message_id)

    def redeliver(self, message: ReceivedMessage) -> None:
        """Simula la reaparición del mensaje al expirar su visibility timeout."""
        self._pending.append(
            ReceivedMessage(
                message_id=message.message_id,
                pop_receipt=message.pop_receipt,
                content=message.content,
                dequeue_count=message.dequeue_count + 1,
            )
        )


def _config(**overrides: object) -> WorkerConfig:
    defaults: dict[str, object] = {
        "poll_interval_seconds": 0.01,
        "visibility_timeout_seconds": 30,
        "max_messages": 16,
        "max_dequeue_count": 5,
    }
    defaults.update(overrides)
    return WorkerConfig(**defaults)  # type: ignore[arg-type]


class TestQueuePump:
    def test_mensaje_procesado_se_borra(self) -> None:
        """El camino feliz: se ejecuta el handler y el mensaje sale de la cola."""
        consumer = FakeConsumer(['{"a":1}', '{"a":2}'])
        procesados: list[str] = []
        pump = QueuePump("transactions", consumer, procesados.append, _config())

        leidos = pump.pump_once()

        assert leidos == 2
        assert procesados == ['{"a":1}', '{"a":2}']
        assert consumer.deleted == ["m0", "m1"]
        assert consumer.dead_lettered == []

    def test_mensaje_que_falla_no_se_borra_y_se_reintenta(self) -> None:
        """Sin borrado no hay pérdida: el mensaje vuelve y acaba procesándose.

        Es la garantía crítica del sistema — un fallo transitorio de Cosmos o
        PostgreSQL no puede hacer desaparecer un caso de fraude.
        """
        consumer = FakeConsumer(['{"tx":"1"}'])
        intentos: list[str] = []

        def handler(content: str) -> None:
            intentos.append(content)
            if len(intentos) == 1:
                raise RuntimeError("Cosmos no disponible")

        pump = QueuePump("transactions", consumer, handler, _config())

        pump.pump_once()
        assert consumer.deleted == []  # el fallo NO consumió el mensaje

        # Al expirar el visibility timeout, la cola lo vuelve a entregar.
        consumer.redeliver(
            ReceivedMessage("m0", "r0", '{"tx":"1"}', dequeue_count=1)
        )
        pump.pump_once()

        assert len(intentos) == 2
        assert consumer.deleted == ["m0"]

    def test_mensaje_envenenado_va_a_la_cola_poison(self) -> None:
        """Superado el máximo de entregas, se aparta en vez de bloquear la cola."""
        consumer = FakeConsumer([])
        consumer._pending.append(
            ReceivedMessage("m9", "r9", "no-es-json", dequeue_count=5)
        )

        def handler(_content: str) -> None:
            raise ValueError("mensaje corrupto")

        pump = QueuePump("cases", consumer, handler, _config(max_dequeue_count=5))
        pump.pump_once()

        assert consumer.dead_lettered == ["m9"]

    def test_un_mensaje_malo_no_impide_procesar_el_resto_del_lote(self) -> None:
        consumer = FakeConsumer(["malo", "bueno"])
        procesados: list[str] = []

        def handler(content: str) -> None:
            if content == "malo":
                raise ValueError("boom")
            procesados.append(content)

        pump = QueuePump("transactions", consumer, handler, _config())
        pump.pump_once()

        assert procesados == ["bueno"]
        assert consumer.deleted == ["m1"]


class TestRunWorker:
    def test_sigterm_detiene_el_bucle(self) -> None:
        """Container Apps manda SIGTERM al escalar a cero: hay que salir, no colgarse."""
        consumer = FakeConsumer([])
        shutdown = threading.Event()
        pump = QueuePump("transactions", consumer, lambda _c: None, _config())

        hilo = threading.Thread(
            target=run_worker, args=([pump], shutdown, _config()), daemon=True
        )
        hilo.start()
        shutdown.set()
        hilo.join(timeout=5)

        assert not hilo.is_alive(), "el worker no atendió la señal de apagado"

    def test_el_bucle_sobrevive_a_un_fallo_de_la_cola(self) -> None:
        """Si Azure Queue no responde, se registra y se reintenta; no se muere."""

        class ConsumidorRoto(FakeConsumer):
            def __init__(self) -> None:
                super().__init__([])
                self.intentos = 0

            def receive(self, max_messages: int, visibility_timeout: int):  # type: ignore[override]
                self.intentos += 1
                raise ConnectionError("storage inalcanzable")

        consumer = ConsumidorRoto()
        shutdown = threading.Event()
        pump = QueuePump("transactions", consumer, lambda _c: None, _config())

        hilo = threading.Thread(
            target=run_worker, args=([pump], shutdown, _config()), daemon=True
        )
        hilo.start()
        threading.Event().wait(0.1)
        shutdown.set()
        hilo.join(timeout=5)

        assert not hilo.is_alive()
        assert consumer.intentos >= 1
