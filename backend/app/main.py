from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.exceptions.auth_exceptions import (
    ForbiddenError,
    UnauthorizedError,
)
from app.domain.exceptions.document_exceptions import (
    DocumentTooLargeError,
    EmptyDocumentError,
    InvalidDocumentTypeError,
)
from app.domain.exceptions.transaction_exceptions import (
    DomainError,
    DuplicateTransactionError,
    InvalidTransactionError,
)
from app.infrastructure.config.settings import settings
from app.presentation.api.middlewares.rate_limit import RateLimitMiddleware
from app.presentation.api.routes.documents import router as documents_router
from app.presentation.api.routes.transactions import router as transactions_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Centinela API",
        version="1.0.0",
        description="API de ingesta de transacciones (Semana 1).",
    )

    app.add_middleware(RateLimitMiddleware, settings=settings)

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

    @app.exception_handler(UnauthorizedError)
    async def unauthorized_handler(
        _request: Request,
        exc: UnauthorizedError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content={"detail": str(exc), "code": "UNAUTHORIZED"},
        )

    @app.exception_handler(ForbiddenError)
    async def forbidden_handler(
        _request: Request,
        exc: ForbiddenError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=403,
            content={"detail": str(exc), "code": "FORBIDDEN"},
        )

    @app.exception_handler(InvalidDocumentTypeError)
    async def invalid_document_type_handler(
        _request: Request,
        exc: InvalidDocumentTypeError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=415,
            content={
                "detail": str(exc),
                "code": "UNSUPPORTED_DOCUMENT_TYPE",
                "contentType": exc.content_type,
            },
        )

    @app.exception_handler(DocumentTooLargeError)
    async def document_too_large_handler(
        _request: Request,
        exc: DocumentTooLargeError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=413,
            content={
                "detail": str(exc),
                "code": "DOCUMENT_TOO_LARGE",
                "sizeBytes": exc.size_bytes,
                "maxBytes": exc.max_bytes,
            },
        )

    @app.exception_handler(EmptyDocumentError)
    async def empty_document_handler(
        _request: Request,
        exc: EmptyDocumentError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "detail": str(exc),
                "code": "EMPTY_DOCUMENT",
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
    app.include_router(documents_router)
    return app


app = create_app()
