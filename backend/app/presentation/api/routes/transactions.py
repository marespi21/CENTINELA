from __future__ import annotations

from fastapi import APIRouter, Depends, status

<<<<<<< HEAD
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

=======
from app.application.dtos.transaction_dto import ReceiveTransactionInput
from app.application.use_cases.receive_transaction import ReceiveTransactionUseCase
from app.presentation.api.dependencies.transactions import get_receive_transaction_use_case
from app.presentation.schemas.transaction_schema import (
    TransactionAcceptedResponse,
    TransactionCreateRequest,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post(
    "",
    response_model=TransactionAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Recibir una transacción",
    description=(
        "Valida y acepta una transacción para procesamiento posterior. "
        "Semana 1: no calcula score ni detecta fraude."
    ),
)
def create_transaction(
    payload: TransactionCreateRequest,
    use_case: ReceiveTransactionUseCase = Depends(get_receive_transaction_use_case),
) -> TransactionAcceptedResponse:
    result = use_case.execute(
        ReceiveTransactionInput(
            transaction_id=payload.transaction_id,
            account_id=payload.account_id,
            amount=payload.amount,
            currency=payload.currency,
            merchant_id=payload.merchant_id,
            merchant_category=payload.merchant_category,
            latitude=payload.latitude,
            longitude=payload.longitude,
        )
    )
    return TransactionAcceptedResponse(
        transaction_id=result.transaction_id,
        status=result.status,
    )
>>>>>>> e9a25c545a4bde0524846c6e6d2e9d6ae6f4e49e
