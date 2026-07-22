from __future__ import annotations

<<<<<<< HEAD
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from backend.app.presentation.api.exception_handlers.http_exceptions import (
    request_validation_exception_handler,
)
from backend.app.presentation.api.routes.transactions import router as transactions_router
=======
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
>>>>>>> e9a25c545a4bde0524846c6e6d2e9d6ae6f4e49e

from app.domain.exceptions.transaction_exceptions import (
    DomainError,
    DuplicateTransactionError,
    InvalidTransactionError,
)
from app.presentation.api.routes.transactions import router as transactions_router

app.add_exception_handler(
    RequestValidationError,
    request_validation_exception_handler,
)


<<<<<<< HEAD
@app.get("/health")
def health() -> dict[str, str]:
    """Health check del servicio."""
    return {"status": "ok"}


app.include_router(transactions_router)

=======
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
>>>>>>> e9a25c545a4bde0524846c6e6d2e9d6ae6f4e49e
