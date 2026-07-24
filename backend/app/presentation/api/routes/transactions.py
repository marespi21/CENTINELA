from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.application.dtos.transaction_dto import ReceiveTransactionInput
from app.application.use_cases.receive_transaction import ReceiveTransactionUseCase
from app.domain.value_objects.role import Role
from app.presentation.api.dependencies.security import Principal, require_roles
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
        "Valida, persiste y publica el evento de transacción. "
        "Responde 202 sin esperar al motor de scoring (desacoplado por cola)."
    ),
)
def create_transaction(
    payload: TransactionCreateRequest,
    use_case: ReceiveTransactionUseCase = Depends(get_receive_transaction_use_case),
    _principal: Principal = Depends(
        require_roles(Role.SERVICIO, Role.ADMINISTRADOR)
    ),
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
