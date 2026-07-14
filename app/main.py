"""FastAPI application entry point for the Centinela API.

Builds the app, configures structured logging and registers the routers. The
title and version feed Swagger UI at ``/docs``.
"""

from __future__ import annotations

from fastapi import FastAPI

from app.api import health, transactions, uploads
from app.core.config import get_settings
from app.core.logger import configure_logging, get_logger


def create_app() -> FastAPI:
    """Application factory: configure logging, build the app, mount routers."""
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_format)
    logger = get_logger(__name__)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Centinela - transactional fraud detection ingestion API (Week 1). "
            "Accepts transactions and file uploads, persisting to Azure Storage."
        ),
    )

    app.include_router(health.router)
    app.include_router(transactions.router)
    app.include_router(uploads.router)

    logger.info(
        "Application initialized",
        extra={"env": settings.app_env, "version": settings.app_version},
    )
    return app


app = create_app()
