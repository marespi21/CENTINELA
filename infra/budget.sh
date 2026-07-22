#!/usr/bin/env bash
# Budget + alertas de costo (módulo Chanti).
# Crea un presupuesto mensual sobre el Resource Group con alertas al 80% y 100%.
# Requiere az login. La sintaxis de 'az consumption budget' varía por versión
# de CLI; si falla, ajustar el bloque de notifications.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=variables.sh
source "${SCRIPT_DIR}/variables.sh"

: "${SUBSCRIPTION_ID:=$(az account show --query id -o tsv)}"
START_DATE="$(date -u +%Y-%m-01)"

echo "==> Creando budget '${BUDGET_NAME}' (${BUDGET_AMOUNT} USD/mes) en ${RESOURCE_GROUP}..."
az consumption budget create \
  --budget-name "${BUDGET_NAME}" \
  --amount "${BUDGET_AMOUNT}" \
  --category Cost \
  --time-grain Monthly \
  --start-date "${START_DATE}" \
  --end-date "2030-01-01" \
  --resource-group "${RESOURCE_GROUP}" \
  --notifications "{
    \"actual_80\":  {\"enabled\": true, \"operator\": \"GreaterThanOrEqualTo\", \"threshold\": 80,  \"contactEmails\": [\"${BUDGET_ALERT_EMAIL}\"]},
    \"actual_100\": {\"enabled\": true, \"operator\": \"GreaterThanOrEqualTo\", \"threshold\": 100, \"contactEmails\": [\"${BUDGET_ALERT_EMAIL}\"]}
  }"

echo "==> Budget configurado."
