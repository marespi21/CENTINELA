"""Punto de entrada de la API CENTINELA."""

from fastapi import FastAPI

app = FastAPI(
    title="CENTINELA",
    description="API de CENTINELA",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Health check del servicio."""
    return {"status": "ok"}
