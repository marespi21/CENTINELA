from __future__ import annotations

from backend.app.application.dtos.transaction import TransactionAckDTO, TransactionInDTO
from backend.app.domain.entities.transaction import Transaction
from backend.app.domain.repositories.transaction_repository import TransactionRepository


class IngestTransactionUseCase:
    def __init__(self, repository: TransactionRepository):
        self._repository = repository

    async def execute(self, dto: TransactionInDTO) -> TransactionAckDTO:
        # Semana 1: no hay lógica de fraude. Solo mapeo y persistencia.
        tx = Transaction(
            transaction_id=dto.transaction_id,
            account_id=dto.account_id,
            amount=dto.amount,
            currency=dto.currency,
            merchant_id=dto.merchant_id,
            merchant_category=dto.merchant_category,
            timestamp=dto.timestamp,
            latitude=dto.latitude,
            longitude=dto.longitude,
        )

        await self._repository.save(tx)

        return TransactionAckDTO(transaction_id=tx.transaction_id, accepted=True)

