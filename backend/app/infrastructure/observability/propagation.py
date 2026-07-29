"""Propagación del contexto de traza a través de las colas (Sprint 6, Fase 3).

El problema que resuelve: hasta ahora la API abría una traza al recibir
`POST /transactions` y el worker abría OTRA al procesar el mensaje. Eran dos
trazas inconexas, así que no había forma de responder a la pregunta que de
verdad importa en producción —"¿por qué este caso tardó 4 minutos en aparecer?"—
porque nada unía la petición HTTP con el scoring que la siguió.

Azure Queue Storage no tiene cabeceras de mensaje: el cuerpo es una cadena. Así
que el contexto W3C (`traceparent` / `tracestate`) viaja **dentro del JSON**,
como dos claves más. Es seguro: todos los parsers del sistema leen las claves
que les interesan e ignoran el resto, de modo que un mensaje con contexto lo
entiende igual un consumidor antiguo.

Como el resto de la observabilidad, degrada a no-op sin OpenTelemetry instalado
o sin colector configurado.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Claves W3C Trace Context. Nombres estándar, no inventados: si algún día otro
# sistema consume estas colas, sabrá interpretarlas.
TRACEPARENT_KEY = "traceparent"
TRACESTATE_KEY = "tracestate"


def inject_trace_context(message: str) -> str:
    """Devuelve el mensaje con el contexto de traza actual incrustado.

    Si el mensaje no es un objeto JSON, o no hay traza activa, se devuelve tal
    cual: la telemetría nunca puede corromper un mensaje de negocio.
    """
    try:
        from opentelemetry.propagate import inject
    except ImportError:  # pragma: no cover - depende de la imagen
        return message

    try:
        payload = json.loads(message)
    except (json.JSONDecodeError, TypeError):
        return message
    if not isinstance(payload, dict):
        return message

    carrier: dict[str, str] = {}
    try:
        inject(carrier)
    except Exception:  # pragma: no cover - defensivo
        logger.debug("no se pudo inyectar el contexto de traza", exc_info=True)
        return message

    if not carrier:
        return message

    payload.update(carrier)
    return json.dumps(payload)


def extract_trace_context(message: str) -> Any:
    """Recupera el contexto de traza del mensaje, o None si no lo trae."""
    try:
        from opentelemetry.propagate import extract
    except ImportError:  # pragma: no cover - depende de la imagen
        return None

    try:
        payload = json.loads(message)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None

    carrier = {
        key: str(payload[key])
        for key in (TRACEPARENT_KEY, TRACESTATE_KEY)
        if payload.get(key)
    }
    if not carrier:
        return None

    try:
        return extract(carrier)
    except Exception:  # pragma: no cover - defensivo
        logger.debug("no se pudo extraer el contexto de traza", exc_info=True)
        return None
