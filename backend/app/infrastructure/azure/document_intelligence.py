"""Adaptador de Azure AI Document Intelligence (Sprint 6, Fase 2).

Capa gratuita **F0**: 500 páginas al mes y concurrencia limitada. Por eso el
worker procesa los documentos de uno en uno desde la cola en vez de en paralelo,
y por eso un documento ilegible NO se reintenta (gastaría cuota para obtener el
mismo resultado).

Autenticación: Managed Identity vía `DefaultAzureCredential` (producción) o
clave (desarrollo). Como el resto de adaptadores, el SDK se importa de forma
perezosa para que las imágenes y los tests que no lo usan no lo carguen.

El parseo de campos es deliberadamente tolerante: entre versiones del SDK los
valores se exponen unas veces como atributos (`value_currency`) y otras como
claves de diccionario (`valueCurrency`), y una excepción aquí convertiría un
documento perfectamente legible en un fallo de servicio.
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.domain.entities.document_analysis import DocumentAnalysis, ExtractedField
from app.domain.repositories.document_analyzer import (
    DocumentAnalysisError,
    DocumentAnalyzer,
)

logger = logging.getLogger(__name__)

# `prebuilt-receipt` cubre tickets y recibos, que es lo que un cliente adjunta
# para respaldar una compra cuestionada. Configurable para poder pasar a
# `prebuilt-invoice` (facturas) sin tocar código.
DEFAULT_MODEL_ID = "prebuilt-receipt"


class AzureDocumentIntelligenceAnalyzer(DocumentAnalyzer):
    def __init__(
        self,
        endpoint: str,
        api_key: str | None = None,
        model_id: str = DEFAULT_MODEL_ID,
    ) -> None:
        from azure.ai.documentintelligence import DocumentIntelligenceClient

        if api_key:
            from azure.core.credentials import AzureKeyCredential

            credential: Any = AzureKeyCredential(api_key)
        else:
            from azure.identity import DefaultAzureCredential

            credential = DefaultAzureCredential()

        self._client = DocumentIntelligenceClient(
            endpoint=endpoint, credential=credential
        )
        self._model_id = model_id

    def analyze(self, content: bytes, content_type: str) -> DocumentAnalysis:
        from azure.core.exceptions import AzureError

        try:
            poller = self._client.begin_analyze_document(
                self._model_id,
                content,
                content_type=content_type or "application/octet-stream",
            )
            result = poller.result()
        except AzureError as exc:
            # Fallo del SERVICIO (caído, cuota agotada, timeout): debe
            # reintentarse, así que se distingue de "documento ilegible".
            raise DocumentAnalysisError(
                f"Document Intelligence no pudo procesar el documento: {exc}"
            ) from exc

        return self._to_analysis(result)

    def _to_analysis(self, result: Any) -> DocumentAnalysis:
        raw_text = _attr(result, "content", "") or ""
        documents = _attr(result, "documents", None) or []
        if not documents:
            logger.info("el OCR no reconoció ningún documento estructurado")
            return DocumentAnalysis(raw_text=raw_text, model_id=self._model_id)

        fields = _attr(documents[0], "fields", None) or {}

        total, total_conf, currency = _read_amount(_field(fields, "Total"))
        date_value, date_conf = _read_date(_field(fields, "TransactionDate"))
        merchant = _read_string(_field(fields, "MerchantName"))

        return DocumentAnalysis(
            total=total,
            total_confidence=total_conf,
            transaction_date=date_value,
            date_confidence=date_conf,
            merchant_name=merchant,
            currency=currency,
            raw_text=raw_text,
            model_id=self._model_id,
            fields={
                name: extracted
                for name, extracted in (
                    (key, _read_string(_field(fields, key)))
                    for key in ("MerchantAddress", "MerchantPhoneNumber", "Subtotal")
                )
                if extracted is not None
            },
        )


# --- lectura tolerante de los campos del SDK ---------------------------------


def _attr(obj: Any, name: str, default: Any = None) -> Any:
    """Lee `name` de un objeto o de un dict, con varias convenciones de nombre."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        camel = name[0] + name.title().replace("_", "")[1:] if "_" in name else name
        for key in (name, camel):
            if key in obj:
                return obj[key]
        return default
    return getattr(obj, name, default)


def _field(fields: Any, key: str) -> Any:
    if isinstance(fields, dict):
        return fields.get(key)
    return getattr(fields, key, None)


def _confidence(field: Any) -> float:
    value = _attr(field, "confidence", 0.0)
    try:
        return float(value) if value is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _read_amount(field: Any) -> tuple[Decimal | None, float, str | None]:
    """Extrae el importe. `prebuilt-receipt` lo devuelve como valor de moneda."""
    if field is None:
        return None, 0.0, None

    currency_value = _attr(field, "value_currency") or _attr(field, "valueCurrency")
    amount: Any = None
    currency_code: str | None = None

    if currency_value is not None:
        amount = _attr(currency_value, "amount")
        currency_code = _attr(currency_value, "currency_code") or _attr(
            currency_value, "currencyCode"
        )
    if amount is None:
        amount = _attr(field, "value_number") or _attr(field, "valueNumber")
    if amount is None:
        amount = _attr(field, "content")

    try:
        parsed = Decimal(str(amount)) if amount is not None else None
    except (InvalidOperation, ValueError):
        parsed = None

    return parsed, _confidence(field), currency_code


def _read_date(field: Any) -> tuple[datetime | None, float]:
    if field is None:
        return None, 0.0

    value = _attr(field, "value_date") or _attr(field, "valueDate")
    if value is None:
        value = _attr(field, "content")
    if value is None:
        return None, 0.0

    if isinstance(value, datetime):
        return value, _confidence(field)

    text = str(value).replace("Z", "+00:00")
    for parse in (
        datetime.fromisoformat,
        lambda raw: datetime.strptime(raw, "%Y-%m-%d"),
        lambda raw: datetime.strptime(raw, "%d/%m/%Y"),
        lambda raw: datetime.strptime(raw, "%m/%d/%Y"),
    ):
        try:
            return parse(text), _confidence(field)
        except (ValueError, TypeError):
            continue
    return None, 0.0


def _read_string(field: Any) -> ExtractedField | None:
    if field is None:
        return None
    value = _attr(field, "value_string") or _attr(field, "valueString")
    if value is None:
        value = _attr(field, "content")
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return ExtractedField(value=text, confidence=_confidence(field))
