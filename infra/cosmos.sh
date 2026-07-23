#!/usr/bin/env bash
# Cosmos DB for NoSQL — Almacén de transacciones y sus scores (módulo Chanti).
#
# Despliega la cuenta Cosmos DB (SQL API) en NIVEL GRATUITO, con la base de
# datos y el contenedor de transacciones. Fija la CLAVE DE PARTICIÓN, el nivel
# de CONSISTENCIA y la política de EXPIRACIÓN (TTL). Ver docs/nosql.md.
#
# Requiere: az login + Resource Group ya creado (deploy.sh, paso 4).
# Idempotente: los 'create' de Cosmos actúan como create-or-update.
#
# IMPORTANTE: la clave de partición NO se puede cambiar tras crear el
# contenedor. Debe fijarse ANTES de la primera escritura. Reejecutar este
# script con otra COSMOS_PARTITION_KEY sobre un contenedor existente fallará;
# para cambiarla hay que recrear el contenedor (migración de datos).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=variables.sh
source "${SCRIPT_DIR}/variables.sh"

echo "==> Registrando provider Microsoft.DocumentDB (idempotente)..."
az provider register --namespace Microsoft.DocumentDB --wait --output none

echo "==> [Cosmos 1/3] Cuenta '${COSMOS_ACCOUNT}' (free tier, consistencia ${COSMOS_CONSISTENCY})..."
az cosmosdb create \
  --name "${COSMOS_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --kind GlobalDocumentDB \
  --locations regionName="${LOCATION}" failoverPriority=0 isZoneRedundant=False \
  --default-consistency-level "${COSMOS_CONSISTENCY}" \
  --enable-free-tier true \
  --output none \
  || {
    echo "  ERROR al crear con --enable-free-tier true."
    echo "  Solo se permite UNA cuenta de nivel gratuito por suscripción."
    echo "  Si ya existe otra, reutilízala o crea esta sin free tier (editar cosmos.sh)."
    exit 1
  }

echo "==> [Cosmos 2/3] Base de datos '${COSMOS_DATABASE}'..."
az cosmosdb sql database create \
  --account-name "${COSMOS_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${COSMOS_DATABASE}" \
  --output none

echo "==> [Cosmos 3/3] Contenedor '${COSMOS_CONTAINER}' (pk=${COSMOS_PARTITION_KEY}, ${COSMOS_THROUGHPUT} RU/s, TTL=${COSMOS_TTL_SECONDS}s)..."
az cosmosdb sql container create \
  --account-name "${COSMOS_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --database-name "${COSMOS_DATABASE}" \
  --name "${COSMOS_CONTAINER}" \
  --partition-key-path "${COSMOS_PARTITION_KEY}" \
  --throughput "${COSMOS_THROUGHPUT}" \
  --ttl "${COSMOS_TTL_SECONDS}" \
  --output none

COSMOS_ENDPOINT="$(az cosmosdb show \
  --name "${COSMOS_ACCOUNT}" --resource-group "${RESOURCE_GROUP}" \
  --query documentEndpoint -o tsv)"

echo
echo "==> Cosmos DB desplegado."
echo "  COSMOS_ACCOUNT    = ${COSMOS_ACCOUNT}"
echo "  COSMOS_ENDPOINT   = ${COSMOS_ENDPOINT}"
echo "  DATABASE          = ${COSMOS_DATABASE}"
echo "  CONTAINER         = ${COSMOS_CONTAINER}"
echo "  PARTITION KEY     = ${COSMOS_PARTITION_KEY}"
echo "  CONSISTENCIA      = ${COSMOS_CONSISTENCY}"
echo "  THROUGHPUT        = ${COSMOS_THROUGHPUT} RU/s (free tier cubre 1000 RU/s)"
echo "  TTL por defecto   = ${COSMOS_TTL_SECONDS} s (~$((COSMOS_TTL_SECONDS / 86400)) días)"
echo
echo "Verificar la partición única (criterio de aceptación):"
echo "  export COSMOS_ENDPOINT=\"${COSMOS_ENDPOINT}\""
echo "  export COSMOS_KEY=\"\$(az cosmosdb keys list --name ${COSMOS_ACCOUNT} --resource-group ${RESOURCE_GROUP} --query primaryMasterKey -o tsv)\""
echo "  python scripts/cosmos_partition_demo.py"
