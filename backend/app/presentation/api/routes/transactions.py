from __future__ import annotations

from fastapi import APIRouter, Depends, status

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
