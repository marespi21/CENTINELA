from __future__ import annotations

import json
from decimal import Decimal
from uuid import uuid4

from app.application.dtos.transaction_dto import ReceiveTransactionInput
from app.application.use_cases.receive_transaction import ReceiveTransactionUseCase
from app.domain.exceptions.transaction_exceptions import DuplicateTransactionError
from app.infrastructure.messaging.in_memory_transaction_event_publisher import (
    InMemoryTransactionEventPublisher,
)
from app.infrastructure.repositories.in_memory_transaction_repository import (
    InMemoryTransactionRepository,
)


def _payload(transaction_id=None) -> ReceiveTransactionInput:
    return ReceiveTransactionInput(
        transaction_id=transaction_id or uuid4(),
        account_id="acc-001",
        amount=Decimal("150000.50"),
        currency="cop",
        merchant_id="mer-9",
        merchant_category="restaurants",
        latitude=Decimal("4.7110"),
        longitude=Decimal("-74.0721"),
    )


def test_receive_transaction_saves_publishes_and_returns_accepted() -> None:
    repository = InMemoryTransactionRepository()
    events = InMemoryTransactionEventPublisher()
    use_case = ReceiveTransactionUseCase(repository, events)

    transaction_id = uuid4()
    result = use_case.execute(_payload(transaction_id))

    assert result.transaction_id == transaction_id
    assert result.status == "accepted"
    assert repository.exists(transaction_id)
    assert len(events.published) == 1
    body = json.loads(events.published[0])
    assert body["event"] == "transaction.received"
    assert body["transactionId"] == str(transaction_id)
    assert body["accountId"] == "acc-001"
    assert "publishedAt" in body


def test_receive_transaction_rejects_duplicates() -> None:
    repository = InMemoryTransactionRepository()
    events = InMemoryTransactionEventPublisher()
    use_case = ReceiveTransactionUseCase(repository, events)
    payload = _payload()

    use_case.execute(payload)

    try:
        use_case.execute(payload)
        assert False, "Expected DuplicateTransactionError"
    except DuplicateTransactionError as exc:
        assert exc.transaction_id == str(payload.transaction_id)

    # El duplicado no genera un segundo evento.
    assert len(events.published) == 1
