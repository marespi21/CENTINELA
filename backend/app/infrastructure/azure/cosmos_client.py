"""Fábrica del cliente de contenedor de Cosmos DB (Semana 3).

Autenticación:
- Con `key`: acceso por clave (útil en local/desarrollo).
- Sin `key`: **Managed Identity** (`DefaultAzureCredential`), sin credenciales
  en código, coherente con el resto de adaptadores Azure.

El SDK se importa de forma perezosa para no exigirlo mientras se trabaja con los
adaptadores en memoria.
"""

from __future__ import annotations

from typing import Any


def get_container_client(
    endpoint: str,
    database: str,
    container: str,
    key: str | None = None,
) -> Any:
    """Devuelve el `ContainerProxy` de Cosmos para (database, container)."""
    from azure.cosmos import CosmosClient

    if key:
        client = CosmosClient(url=endpoint, credential=key)
    else:
        from azure.identity import DefaultAzureCredential

        client = CosmosClient(url=endpoint, credential=DefaultAzureCredential())

    return client.get_database_client(database).get_container_client(container)
