"""Punto de entrada de la API CENTINELA."""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from backend.app.presentation.api.exception_handlers.http_exceptions import (
    request_validation_exception_handler,
)
from backend.app.presentation.api.routes.transactions import router as transactions_router

app = FastAPI(
    title="CENTINELA",
    description="API de CENTINELA",
    version="0.1.0",
)

app.add_exception_handler(
    RequestValidationError,
    request_validation_exception_handler,
)


@app.get("/health")
def health() -> dict[str, str]:
    """Health check del servicio."""
    return {"status": "ok"}


app.include_router(transactions_router)

