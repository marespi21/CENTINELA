#!/usr/bin/env bash
# Acceso privado (integración Juanjo + Samuel): VNet integration + Private
# Endpoint del storage + cierre del acceso público.
#
# Prerrequisitos:
#   - VNet/subnets creadas por scripts/deploy-network.sh (mismos nombres).
#   - App Service SKU B1+ (F1 Free NO soporta VNet integration).
#   - La subnet de la app debe estar delegada a Microsoft.Web.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=variables.sh
source "${SCRIPT_DIR}/variables.sh"

echo "==> Integrando la Web App a la subnet ${SUBNET_APP}..."
az webapp vnet-integration add \
  --resource-group "${RESOURCE_GROUP}" --name "${WEBAPP}" \
  --vnet "${VNET}" --subnet "${SUBNET_APP}" \
  --output none

echo "==> Creando Private Endpoint del blob en ${SUBNET_DATA}..."
STORAGE_ID="$(az storage account show \
  --resource-group "${RESOURCE_GROUP}" --name "${STORAGE_ACCOUNT}" \
  --query id -o tsv)"

az network private-endpoint create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "pe-${STORAGE_ACCOUNT}-blob" \
  --vnet-name "${VNET}" --subnet "${SUBNET_DATA}" \
  --private-connection-resource-id "${STORAGE_ID}" \
  --group-id blob \
  --connection-name "conn-${STORAGE_ACCOUNT}-blob" \
  --output none

echo "==> Cerrando acceso público del storage (default Deny)..."
az storage account update \
  --resource-group "${RESOURCE_GROUP}" --name "${STORAGE_ACCOUNT}" \
  --default-action Deny \
  --bypass AzureServices \
  --output none

echo "==> Acceso privado configurado."
