from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.application.dtos.transaction_dto import (
    ReceiveTransactionInput,
    ReceiveTransactionOutput,
)
from app.domain.entities.transaction import Transaction
from app.domain.exceptions.transaction_exceptions import (
    DuplicateTransactionError,
    InvalidTransactionError,
)
from app.domain.repositories.transaction_event_publisher import (
    TransactionEventPublisher,
)
from app.domain.repositories.transaction_repository import TransactionRepository


class ReceiveTransactionUseCase:
    """Recibe una transacción, la persiste y publica el evento de scoring.

    Secuencia (semana 2):
    1. Validar contrato
    2. Persistir
    3. Publicar evento en la cola de transacciones
    4. Responder acuse (202)

    El motor de scoring NO se invoca aquí: reacciona al evento de forma
    asíncrona. La publicación solo espera a que la cola acepte el mensaje.
    """

    def __init__(
        self,
        repository: TransactionRepository,
        event_publisher: TransactionEventPublisher,
    ) -> None:
        self._repository = repository
        self._events = event_publisher

    def execute(self, data: ReceiveTransactionInput) -> ReceiveTransactionOutput:
        self._validate(data)

        if self._repository.exists(data.transaction_id):
            raise DuplicateTransactionError(str(data.transaction_id))

        transaction = Transaction(
            transaction_id=data.transaction_id,
            account_id=data.account_id,
            amount=data.amount,
            currency=data.currency.upper(),
            merchant_id=data.merchant_id,
            merchant_category=data.merchant_category,
            timestamp=datetime.now(timezone.utc),
            latitude=data.latitude,
            longitude=data.longitude,
        )

        self._repository.save(transaction)
        # Punto de inserción de mensajería (req. 2.4): publicar y seguir.
        # No se espera al scoring.
        self._events.publish(transaction)

        return ReceiveTransactionOutput(transaction_id=transaction.transaction_id)

    def _validate(self, data: ReceiveTransactionInput) -> None:
        if not data.account_id.strip():
            raise InvalidTransactionError("accountId is required")
        if not data.merchant_id.strip():
            raise InvalidTransactionError("merchantId is required")
        if not data.merchant_category.strip():
            raise InvalidTransactionError("merchantCategory is required")
        if not data.currency.strip():
            raise InvalidTransactionError("currency is required")
        if data.amount <= Decimal("0"):
            raise InvalidTransactionError("amount must be greater than 0")
        if data.latitude < Decimal("-90") or data.latitude > Decimal("90"):
            raise InvalidTransactionError("latitude must be between -90 and 90")
        if data.longitude < Decimal("-180") or data.longitude > Decimal("180"):
            raise InvalidTransactionError("longitude must be between -180 and 180")
