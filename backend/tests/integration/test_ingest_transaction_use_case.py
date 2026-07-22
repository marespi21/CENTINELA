import pytest
from uuid import uuid4
from datetime import datetime, timezone

from backend.app.application.dtos.transaction import TransactionInDTO
from backend.app.application.use_cases.ingest_transaction import IngestTransactionUseCase
from backend.app.domain.entities.transaction import Transaction
from backend.app.domain.repositories.transaction_repository import TransactionRepository


class FakeRepo(TransactionRepository):
    def __init__(self) -> None:
        self.saved: list[Transaction] = []

    async def save(self, tx: Transaction) -> None:
        self.saved.append(tx)


@pytest.mark.asyncio
async def test_use_case_persists_transaction_and_returns_ack():
    repo = FakeRepo()
    use_case = IngestTransactionUseCase(repository=repo)

    dto = TransactionInDTO(
        transaction_id=uuid4(),
        account_id="acc_1",
        amount=10.0,
        currency="COP",
        merchant_id="m1",
        merchant_category="cat1",
        timestamp=datetime.now(timezone.utc),
        latitude=1.0,
        longitude=2.0,
    )

    ack = await use_case.execute(dto)

    assert ack.accepted is True
    assert ack.transaction_id == dto.transaction_id
    assert len(repo.saved) == 1
    assert repo.saved[0].transaction_id == dto.transaction_id

