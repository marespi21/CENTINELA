#!/usr/bin/env python3
"""Demostración de partición única — Cosmos DB (módulo Chanti, CENTINELA).

Evidencia el criterio de aceptación de la semana 2:

    "La consulta de historial de UNA cuenta toca una sola partición."

Para ello:
  1. Siembra transacciones de ejemplo repartidas en varias cuentas.
  2. Ejecuta la consulta de historial CON clave de partición -> Cosmos la enruta
     a una única partición física (lectura single-partition).
  3. Ejecuta la MISMA consulta SIN clave de partición -> el motor debe abanicar
     (fan-out) consultando el mapa de particiones.
  4. Imprime el costo en Request Units (header 'x-ms-request-charge') de cada
     una. La consulta dirigida a la partición es la que se registra en el
     reporte de crédito (docs/credit-report-nosql.md).

Uso:
    export COSMOS_ENDPOINT="https://cosmos-centinela-dev.documents.azure.com:443/"
    export COSMOS_KEY="$(az cosmosdb keys list \\
        --name cosmos-centinela-dev --resource-group rg-centinela-dev \\
        --query primaryMasterKey -o tsv)"
    python scripts/cosmos_partition_demo.py

Requiere: pip install -r scripts/requirements.txt
NUNCA versiones la clave: úsala solo desde la terminal para la demostración.
"""
from __future__ import annotations

import os
import random
import sys
import uuid
from datetime import datetime, timezone

try:
    from azure.cosmos import CosmosClient
except ImportError:
    sys.exit("Falta azure-cosmos. Instala con: pip install -r scripts/requirements.txt")

DATABASE = os.environ.get("COSMOS_DATABASE", "centinela")
CONTAINER = os.environ.get("COSMOS_CONTAINER", "transactions")

ACCOUNTS = [f"acc-{i:03d}" for i in range(1, 6)]  # 5 cuentas
TX_PER_ACCOUNT = 6                                # 30 transacciones en total

QUERY = "SELECT * FROM c WHERE c.accountId = @acc"


def _last_charge(container) -> float:
    """RU cobradas en la última respuesta del data plane."""
    headers = container.client_connection.last_response_headers
    return float(headers.get("x-ms-request-charge", 0.0))


def seed(container) -> None:
    total = len(ACCOUNTS) * TX_PER_ACCOUNT
    print(f"Sembrando {total} transacciones en {len(ACCOUNTS)} cuentas...")
    for account in ACCOUNTS:
        for _ in range(TX_PER_ACCOUNT):
            container.upsert_item({
                "id": str(uuid.uuid4()),
                "accountId": account,
                "amount": round(random.uniform(10, 5000), 2),
                "score": round(random.random(), 4),
                "createdAt": datetime.now(timezone.utc).isoformat(),
            })


def query_single_partition(container, account):
    """Historial de la cuenta enrutado a una sola partición (pasa partition_key)."""
    items = list(container.query_items(
        query=QUERY,
        parameters=[{"name": "@acc", "value": account}],
        partition_key=account,
    ))
    return len(items), _last_charge(container)


def query_cross_partition(container, account):
    """Misma consulta sin partition_key: el motor abanica entre particiones."""
    items = list(container.query_items(
        query=QUERY,
        parameters=[{"name": "@acc", "value": account}],
    ))
    return len(items), _last_charge(container)


def main() -> int:
    endpoint = os.environ.get("COSMOS_ENDPOINT")
    key = os.environ.get("COSMOS_KEY")
    if not endpoint or not key:
        sys.exit("Define COSMOS_ENDPOINT y COSMOS_KEY (ver encabezado del script).")

    client = CosmosClient(endpoint, credential=key)
    container = client.get_database_client(DATABASE).get_container_client(CONTAINER)

    seed(container)
    account = ACCOUNTS[0]

    n_single, ru_single = query_single_partition(container, account)
    n_cross, ru_cross = query_cross_partition(container, account)

    print()
    print(f"Historial de la cuenta '{account}':")
    print(f"  CON clave de partición (1 partición) : {n_single} items · {ru_single:.2f} RU")
    print(f"  SIN clave de partición (fan-out)     : {n_cross} items · {ru_cross:.2f} RU")
    print()
    print("La consulta CON clave de partición se enruta a una única partición")
    print("física; es la que debe registrarse en el reporte de crédito.")
    if ru_single <= ru_cross:
        print(f"OK: es {ru_cross - ru_single:.2f} RU más barata que el fan-out.")
    else:
        print("Nota: con pocos datos puede existir una sola partición física y el")
        print("costo puede empatar; la enrutada sigue tocando una sola partición.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
