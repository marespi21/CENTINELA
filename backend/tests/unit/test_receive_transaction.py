from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from app.application.dtos.transaction_dto import ReceiveTransactionInput
from app.application.use_cases.receive_transaction import ReceiveTransactionUseCase
from app.domain.exceptions.transaction_exceptions import DuplicateTransactionError
from app.infrastructure.repositories.in_memory_transaction_repository import (
    InMemoryTransactionRepository,
)


def test_receive_transaction_saves_and_returns_accepted() -> None:
    repository = InMemoryTransactionRepository()
    use_case = ReceiveTransactionUseCase(repository)

    transaction_id = uuid4()
    result = use_case.execute(
        ReceiveTransactionInput(
            transaction_id=transaction_id,
            account_id="acc-001",
            amount=Decimal("150000.50"),
            currency="cop",
            merchant_id="mer-9",
            merchant_category="restaurants",
            latitude=Decimal("4.7110"),
            longitude=Decimal("-74.0721"),
        )
    )

    assert result.transaction_id == transaction_id
    assert result.status == "accepted"
    assert repository.exists(transaction_id)


def test_receive_transaction_rejects_duplicates() -> None:
    repository = InMemoryTransactionRepository()
    use_case = ReceiveTransactionUseCase(repository)
    transaction_id = uuid4()
    payload = ReceiveTransactionInput(
        transaction_id=transaction_id,
        account_id="acc-001",
        amount=Decimal("10.00"),
        currency="USD",
        merchant_id="mer-1",
        merchant_category="retail",
        latitude=Decimal("0"),
        longitude=Decimal("0"),
    )

    use_case.execute(payload)

    try:
        use_case.execute(payload)
        assert False, "Expected DuplicateTransactionError"
    except DuplicateTransactionError as exc:
        assert exc.transaction_id == str(transaction_id)
