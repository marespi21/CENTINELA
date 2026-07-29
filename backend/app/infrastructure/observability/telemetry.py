"""Instrumentación OpenTelemetry — se activa por configuración, nunca por defecto.

Regla de diseño (Sprint 6): la telemetría se añade **a medida que se
contenedoriza**, pero no puede volverse un requisito de arranque. Por eso este
módulo es tolerante a fallos en dos ejes:

1. **Sin endpoint** (`OTEL_EXPORTER_OTLP_ENDPOINT` vacío) → no-op. Es el caso de
   los tests, del desarrollo local y del despliegue anterior en App Service /
   Azure Functions, que siguen funcionando sin cambios.
2. **Sin los paquetes instalados** → no-op. La imagen del worker no arrastra el
   instrumentador de FastAPI, y `requirements.txt` (App Service) no incluye
   OpenTelemetry en absoluto.

En Azure Container Apps el agente OTel gestionado del *environment* inyecta
`OTEL_EXPORTER_OTLP_ENDPOINT` en el contenedor y reenvía a Application Insights;
la aplicación solo habla OTLP/HTTP contra localhost, sin credenciales de ningún
tipo dentro de la imagen.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_configured = False


def telemetry_enabled() -> bool:
    """True si hay un colector OTLP configurado al que exportar."""
    return bool(os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip())


def setup_telemetry(service_name: str, service_version: str = "1.0.0") -> bool:
    """Configura el proveedor de trazas y métricas. Idempotente.

    Devuelve True si la telemetría quedó activa. Nunca lanza: un fallo de
    observabilidad no puede tumbar el contenedor.
    """
    global _configured
    if _configured:
        return True
    if not telemetry_enabled():
        logger.info("telemetría OTLP deshabilitada (sin OTEL_EXPORTER_OTLP_ENDPOINT)")
        return False

    try:
        from opentelemetry import metrics, trace
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
            OTLPMetricExporter,
        )
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:  # pragma: no cover - depende de la imagen
        logger.info("telemetría OTLP no disponible (paquetes no instalados)")
        return False

    try:
        resource = Resource.create(
            {
                "service.name": service_name,
                "service.version": service_version,
                "deployment.environment": os.getenv("ENVIRONMENT", "development"),
            }
        )
        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        trace.set_tracer_provider(tracer_provider)

        # Métricas: se respeta la convención estándar `OTEL_METRICS_EXPORTER`.
        #
        # Hace falta porque no todos los colectores aceptan métricas aunque
        # acepten trazas. El agente gestionado de Azure Container Apps es justo
        # ese caso: reenvía trazas y logs a Application Insights, pero NO
        # métricas. Exportarlas contra él resetea la conexión y el SDK entra en
        # un bucle de reintentos que quema CPU y ahoga los logs con avisos.
        if os.getenv("OTEL_METRICS_EXPORTER", "otlp").strip().lower() != "none":
            metrics.set_meter_provider(
                MeterProvider(
                    resource=resource,
                    metric_readers=[
                        PeriodicExportingMetricReader(OTLPMetricExporter())
                    ],
                )
            )
        else:
            logger.info(
                "exportación de métricas deshabilitada (OTEL_METRICS_EXPORTER=none); "
                "las trazas siguen activas"
            )
    except Exception:  # pragma: no cover - defensivo
        logger.exception("no se pudo configurar la telemetría; se continúa sin ella")
        return False

    _configured = True
    logger.info("telemetría OTLP activa para service.name=%s", service_name)
    return True


def instrument_fastapi(app: Any) -> None:
    """Auto-instrumenta la app FastAPI si el paquete está disponible y hay endpoint."""
    if not _configured:
        return
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    except ImportError:  # pragma: no cover - depende de la imagen
        return
    try:
        FastAPIInstrumentor.instrument_app(app, excluded_urls="health")
    except Exception:  # pragma: no cover - defensivo
        logger.exception("no se pudo instrumentar FastAPI")


def get_tracer(name: str) -> Any:
    """Tracer real si hay telemetría; si no, uno inerte (API idéntica)."""
    try:
        from opentelemetry import trace
    except ImportError:  # pragma: no cover - depende de la imagen
        return _NoopTracer()
    return trace.get_tracer(name)


def get_counter(meter_name: str, counter_name: str, description: str) -> Any:
    """Contador real si hay telemetría; si no, uno inerte (API idéntica)."""
    try:
        from opentelemetry import metrics
    except ImportError:  # pragma: no cover - depende de la imagen
        return _NoopCounter()
    return metrics.get_meter(meter_name).create_counter(
        counter_name, description=description
    )


def get_histogram(
    meter_name: str, histogram_name: str, description: str, unit: str = "ms"
) -> Any:
    """Histograma real si hay telemetría; si no, uno inerte (API idéntica).

    Para latencias se prefiere histograma antes que un contador con media: la
    media esconde justo lo que interesa mirar, que es la cola de percentiles.
    """
    try:
        from opentelemetry import metrics
    except ImportError:  # pragma: no cover - depende de la imagen
        return _NoopHistogram()
    return metrics.get_meter(meter_name).create_histogram(
        histogram_name, description=description, unit=unit
    )


class _NoopSpan:
    def __enter__(self) -> _NoopSpan:
        return self

    def __exit__(self, *_exc: object) -> bool:
        return False

    def set_attribute(self, *_args: object, **_kwargs: object) -> None:
        return None

    def record_exception(self, *_args: object, **_kwargs: object) -> None:
        return None

    def set_status(self, *_args: object, **_kwargs: object) -> None:
        return None


class _NoopTracer:
    def start_as_current_span(self, *_args: object, **_kwargs: object) -> _NoopSpan:
        return _NoopSpan()


class _NoopCounter:
    def add(self, *_args: object, **_kwargs: object) -> None:
        return None


class _NoopHistogram:
    def record(self, *_args: object, **_kwargs: object) -> None:
        return None
