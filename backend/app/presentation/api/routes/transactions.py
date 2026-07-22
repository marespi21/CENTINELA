from __future__ import annotations

from fastapi import APIRouter, Depends, status

from backend.app.application.dtos.transaction import TransactionInDTO
from backend.app.presentation.api.dependencies.container import get_container
from backend.app.presentation.schemas.transaction import TransactionInSchema


router = APIRouter(tags=["transactions"], prefix="/api/v1")


@router.post("/transactions", status_code=status.HTTP_202_ACCEPTED)
async def ingest_transaction(
    payload: TransactionInSchema,
):
    container = get_container()

    dto = TransactionInDTO(
        transaction_id=payload.transactionId,
        account_id=payload.accountId,
        amount=payload.amount,
        currency=payload.currency,
        merchant_id=payload.merchantId,
        merchant_category=payload.merchantCategory,
        timestamp=payload.timestamp,
        latitude=payload.location.latitude,
        longitude=payload.location.longitude,
    )

    ack = await container.ingest_transaction_use_case.execute(dto)
    return {"transactionId": str(ack.transaction_id), "accepted": ack.accepted}

