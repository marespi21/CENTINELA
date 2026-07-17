from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.exceptions.transaction_exceptions import (
    DomainError,
    DuplicateTransactionError,
    InvalidTransactionError,
)
from app.presentation.api.routes.transactions import router as transactions_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Centinela API",
        version="1.0.0",
        description="API de ingesta de transacciones (Semana 1).",
    )

    @app.get("/")
    def root() -> dict[str, str]:
        return {
            "status": "running",
            "service": "Centinela",
        }

    @app.exception_handler(DuplicateTransactionError)
    async def duplicate_transaction_handler(
        _request: Request,
        exc: DuplicateTransactionError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={
                "detail": str(exc),
                "code": "DUPLICATE_TRANSACTION",
                "transactionId": exc.transaction_id,
            },
        )

    @app.exception_handler(InvalidTransactionError)
    async def invalid_transaction_handler(
        _request: Request,
        exc: InvalidTransactionError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "detail": str(exc),
                "code": "INVALID_TRANSACTION",
            },
        )

    @app.exception_handler(DomainError)
    async def domain_error_handler(
        _request: Request,
        exc: DomainError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={
                "detail": str(exc),
                "code": "DOMAIN_ERROR",
            },
        )

    app.include_router(transactions_router)
    return app


app = create_app()
