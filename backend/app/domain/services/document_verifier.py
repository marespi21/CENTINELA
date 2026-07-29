"""Contraste entre el comprobante extraído y la transacción del caso.

Servicio de dominio puro: sin IO, sin SDK, sin base de datos. Toda la decisión
de "este papel respalda o contradice la transacción" vive aquí y se prueba sin
levantar nada.

Qué manda el veredicto y qué no:

- **Importe y fecha mandan.** Son hechos comparables sin ambigüedad y una
  discrepancia en cualquiera de los dos es señal fuerte de fraude.
- **El comercio es informativo.** La transacción guarda `merchant_id` (un
  identificador opaco, `m1`), no un nombre comercial; compararlo contra el
  nombre impreso en el ticket produciría discrepancias falsas constantemente.
  Se registra en el desglose para que el analista lo vea, pero por sí solo NO
  puede dictar DISCREPA.
- **La confianza del OCR filtra antes de juzgar.** Un campo leído por debajo del
  umbral se ignora: no cuenta a favor ni en contra. Acusar de fraude por una
  cifra mal reconocida sería peor que no decir nada.
"""

from __future__ import annotations

from decimal import Decimal

from app.domain.entities.document_analysis import DocumentAnalysis
from app.domain.entities.document_verification import (
    DocumentVerification,
    FieldComparison,
    VerificationVerdict,
)
from app.domain.entities.transaction import Transaction
from app.domain.value_objects.verification_config import VerificationConfig


class DocumentVerifier:
    def __init__(self, config: VerificationConfig | None = None) -> None:
        self._config = config or VerificationConfig()

    def verify(
        self, analysis: DocumentAnalysis, transaction: Transaction
    ) -> DocumentVerification:
        if analysis.is_empty:
            return DocumentVerification(
                verdict=VerificationVerdict.ILEGIBLE,
                summary="El OCR no extrajo ningún dato contrastable del documento.",
            )

        comparisons: list[FieldComparison] = []
        decisive: list[FieldComparison] = []

        amount = self._compare_amount(analysis, transaction)
        if amount is not None:
            comparisons.append(amount)
            decisive.append(amount)

        date = self._compare_date(analysis, transaction)
        if date is not None:
            comparisons.append(date)
            decisive.append(date)

        merchant = self._compare_merchant(analysis, transaction)
        if merchant is not None:
            comparisons.append(merchant)  # informativo: no entra en `decisive`

        if not decisive:
            return DocumentVerification(
                verdict=VerificationVerdict.INSUFICIENTE,
                comparisons=comparisons,
                summary=(
                    "Se leyó el documento, pero ningún campo contrastable superó "
                    "el umbral de confianza."
                ),
            )

        mismatches = [c for c in decisive if not c.matches]
        if mismatches:
            campos = ", ".join(c.field_name for c in mismatches)
            return DocumentVerification(
                verdict=VerificationVerdict.DISCREPA,
                comparisons=comparisons,
                summary=f"El comprobante contradice la transacción en: {campos}.",
            )

        return DocumentVerification(
            verdict=VerificationVerdict.COINCIDE,
            comparisons=comparisons,
            summary=(
                f"El comprobante respalda la transacción "
                f"({len(decisive)} campo(s) contrastado(s))."
            ),
        )

    # -- comparaciones individuales -----------------------------------------

    def _compare_amount(
        self, analysis: DocumentAnalysis, transaction: Transaction
    ) -> FieldComparison | None:
        if analysis.total is None:
            return None
        if analysis.total_confidence < self._config.min_field_confidence:
            return None

        expected = transaction.amount
        difference = abs(analysis.total - expected)
        # Se admite la mayor de las dos tolerancias: la relativa gobierna en
        # importes altos y la absoluta evita falsos positivos en los bajos.
        allowed = max(
            expected * self._config.amount_tolerance_ratio,
            self._config.amount_tolerance_absolute,
        )
        matches = difference <= allowed

        return FieldComparison(
            field_name="importe",
            document_value=f"{analysis.total}",
            transaction_value=f"{expected}",
            matches=matches,
            detail=(
                f"diferencia de {difference} sobre una tolerancia de {allowed}"
                if not matches
                else f"dentro de la tolerancia ({difference} ≤ {allowed})"
            ),
        )

    def _compare_date(
        self, analysis: DocumentAnalysis, transaction: Transaction
    ) -> FieldComparison | None:
        if analysis.transaction_date is None:
            return None
        if analysis.date_confidence < self._config.min_field_confidence:
            return None

        doc_date = analysis.transaction_date
        tx_date = transaction.timestamp
        # Comparar un naive con un aware revienta; se normaliza al huso de la
        # transacción, que es el dato de referencia.
        if doc_date.tzinfo is None and tx_date.tzinfo is not None:
            doc_date = doc_date.replace(tzinfo=tx_date.tzinfo)
        elif doc_date.tzinfo is not None and tx_date.tzinfo is None:
            tx_date = tx_date.replace(tzinfo=doc_date.tzinfo)

        delta_days = abs((doc_date - tx_date).days)
        matches = delta_days <= self._config.date_window_days

        return FieldComparison(
            field_name="fecha",
            document_value=doc_date.date().isoformat(),
            transaction_value=tx_date.date().isoformat(),
            matches=matches,
            detail=(
                f"{delta_days} día(s) de diferencia; la ventana admitida es "
                f"{self._config.date_window_days}"
            ),
        )

    def _compare_merchant(
        self, analysis: DocumentAnalysis, transaction: Transaction
    ) -> FieldComparison | None:
        if analysis.merchant_name is None:
            return None
        if analysis.merchant_name.confidence < self._config.min_field_confidence:
            return None

        document_value = analysis.merchant_name.value.strip()
        expected = transaction.merchant_id.strip()
        # Coincidencia laxa por contención normalizada: `merchant_id` es opaco,
        # así que esto acierta poco y por eso el campo no es decisivo.
        normalized_doc = document_value.casefold()
        normalized_tx = expected.casefold()
        matches = bool(normalized_tx) and (
            normalized_tx in normalized_doc or normalized_doc in normalized_tx
        )

        return FieldComparison(
            field_name="comercio",
            document_value=document_value,
            transaction_value=expected,
            matches=matches,
            detail=(
                "informativo: la transacción guarda un identificador de comercio, "
                "no su nombre comercial, así que este campo no decide el veredicto"
            ),
        )


def decimal_or_none(value: object) -> Decimal | None:
    """Convierte a Decimal lo que venga del OCR, o None si no es un número."""
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (ArithmeticError, ValueError):
        return None
