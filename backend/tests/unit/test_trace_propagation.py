"""Tests de la propagación de traza por las colas (Sprint 6, Fase 3).

Esto es lo que puede romperse sin que nadie se entere: si la inyección deja de
funcionar, el sistema sigue procesando transacciones con normalidad y solo se
degradan las trazas. Por eso conviene tenerlo cubierto explícitamente.

Los tests no requieren colector OTLP: montan un proveedor de trazas en memoria.
"""

from __future__ import annotations

import json

import pytest

from app.infrastructure.observability.propagation import (
    TRACEPARENT_KEY,
    extract_trace_context,
    inject_trace_context,
)

pytest.importorskip("opentelemetry.sdk", reason="OpenTelemetry no instalado")


@pytest.fixture
def tracer():
    """Proveedor de trazas en memoria, aislado de la configuración global."""
    from opentelemetry.sdk.trace import TracerProvider

    return TracerProvider().get_tracer("test")


class TestInyeccion:
    def test_el_mensaje_sale_con_traceparent_cuando_hay_traza(self, tracer) -> None:
        original = json.dumps({"event": "transaction.received", "amount": "100"})

        with tracer.start_as_current_span("publicar"):
            resultado = inject_trace_context(original)

        payload = json.loads(resultado)
        assert TRACEPARENT_KEY in payload
        # El contenido de negocio se conserva intacto.
        assert payload["event"] == "transaction.received"
        assert payload["amount"] == "100"

    def test_sin_traza_activa_el_mensaje_no_cambia(self) -> None:
        original = json.dumps({"event": "transaction.received"})

        assert json.loads(inject_trace_context(original)) == json.loads(original)

    def test_un_mensaje_no_json_se_devuelve_intacto(self, tracer) -> None:
        """La telemetría nunca puede corromper un mensaje de negocio."""
        with tracer.start_as_current_span("publicar"):
            assert inject_trace_context("no soy json") == "no soy json"
            assert inject_trace_context("[1,2,3]") == "[1,2,3]"


class TestExtraccion:
    def test_el_consumidor_recupera_la_traza_del_productor(self, tracer) -> None:
        """La prueba que de verdad importa: un solo trace_id de punta a punta."""
        with tracer.start_as_current_span("publicar") as span_productor:
            trace_id_original = span_productor.get_span_context().trace_id
            mensaje = inject_trace_context(json.dumps({"event": "x"}))

        contexto = extract_trace_context(mensaje)
        assert contexto is not None

        with tracer.start_as_current_span("procesar", context=contexto) as span_consumidor:
            assert span_consumidor.get_span_context().trace_id == trace_id_original

    def test_mensaje_sin_contexto_devuelve_none(self) -> None:
        """Mensajes publicados antes de esta fase siguen procesándose."""
        assert extract_trace_context(json.dumps({"event": "x"})) is None

    def test_mensaje_corrupto_no_revienta_la_extraccion(self) -> None:
        assert extract_trace_context("{roto") is None
        assert extract_trace_context("") is None


class TestCompatibilidad:
    def test_los_parsers_existentes_ignoran_el_contexto(self, tracer) -> None:
        """El contrato de cola no se rompe: `traceparent` es una clave más.

        Si esto fallara, un mensaje con traza tumbaría al worker — mucho peor
        que no tener trazas.
        """
        from app.application.dtos.scoring_dto import transaction_from_event

        evento = json.dumps(
            {
                "event": "transaction.received",
                "transactionId": "11111111-1111-1111-1111-111111111111",
                "accountId": "acc-1",
                "amount": "150000.50",
                "currency": "COP",
                "merchantId": "m1",
                "merchantCategory": "retail",
                "timestamp": "2026-07-23T12:00:00Z",
                "latitude": "4.7110",
                "longitude": "-74.0721",
            }
        )
        with tracer.start_as_current_span("publicar"):
            con_traza = inject_trace_context(evento)

        transaccion = transaction_from_event(con_traza)

        assert transaccion.account_id == "acc-1"
        assert str(transaccion.amount) == "150000.50"

    def test_el_evento_de_documento_tambien_sobrevive(self, tracer) -> None:
        from app.application.dtos.document_event import document_event_from_message

        evento = json.dumps(
            {
                "event": "document.uploaded",
                "blobName": "doc.pdf",
                "filename": "doc.pdf",
                "contentType": "application/pdf",
                "caseId": "caso-1",
            }
        )
        with tracer.start_as_current_span("publicar"):
            parsed = document_event_from_message(inject_trace_context(evento))

        assert parsed.blob_name == "doc.pdf"
        assert parsed.case_id == "caso-1"


class TestTrazarNoEsExportar:
    """Regresión: desactivar la exportación no puede matar los `trace_id`.

    Ocurrió en producción (Sprint 6, Fase 3). El agente OTel de Container Apps
    no aceptaba nada, así que se desactivó la exportación — y con ella
    desaparecieron los identificadores de traza, que eran justo lo que estaba
    dando valor: sin ellos no se puede seguir una petición de la API al worker
    a través de la cola mirando los logs.

    La causa era hacer depender la inicialización del proveedor de que existiera
    un endpoint al que exportar. Son decisiones independientes.
    """

    def test_hay_trazas_aunque_no_haya_a_donde_exportarlas(self, monkeypatch) -> None:
        import app.infrastructure.observability.telemetry as telemetry

        monkeypatch.setattr(telemetry, "_configured", False)
        monkeypatch.setenv("OTEL_TRACES_EXPORTER", "none")
        # También las métricas: si no, el test monta un exportador real que
        # intenta salir a la red y ensucia la salida con errores de timeout.
        monkeypatch.setenv("OTEL_METRICS_EXPORTER", "none")
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

        assert telemetry.setup_telemetry("prueba") is True

        from opentelemetry import trace

        with telemetry.get_tracer("t").start_as_current_span("s"):
            assert trace.get_current_span().get_span_context().is_valid

    def test_sin_configuracion_alguna_sigue_siendo_no_op(self, monkeypatch) -> None:
        """No romper el caso de tests y desarrollo local: sin nada, nada."""
        import app.infrastructure.observability.telemetry as telemetry

        monkeypatch.setattr(telemetry, "_configured", False)
        monkeypatch.delenv("OTEL_TRACES_EXPORTER", raising=False)
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

        assert telemetry.setup_telemetry("prueba") is False
