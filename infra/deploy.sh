#!/usr/bin/env bash
# Despliegue de infraestructura CENTINELA (Azure CLI).
# Uso: bash infra/deploy.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=variables.sh
source "${SCRIPT_DIR}/variables.sh"

echo "==> Desplegando ${PROJECT} (${ENV}) en ${LOCATION}"
echo "    Resource group: ${RESOURCE_GROUP}"
echo

# Registrar providers necesarios (idempotente)
echo "[0/11] Registrando providers Azure..."
az provider register --namespace Microsoft.Storage --wait --output none
az provider register --namespace Microsoft.Web --wait --output none

# --- Paso 4: Resource Group ---
echo "[4/11] Creando Resource Group..."
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --output none

# --- Paso 5: Storage Account ---
echo "[5/11] Creando Storage Account..."
az storage account create \
  --name "${STORAGE_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --allow-blob-public-access false \
  --output none

# --- Paso 6: Blob Container (privado) ---
echo "[6/11] Creando Blob Container '${BLOB_CONTAINER}'..."
az storage container create \
  --account-name "${STORAGE_ACCOUNT}" \
  --name "${BLOB_CONTAINER}" \
  --public-access off \
  --auth-mode login \
  --output none

# --- Paso 6.5: Lifecycle policy (módulo Samuel) ---
echo "[6.5] Aplicando lifecycle policy (cool->archive->delete)..."
az storage account management-policy create \
  --account-name "${STORAGE_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --policy "@${SCRIPT_DIR}/lifecycle-policy.json" \
  --output none

# --- Paso: 7 Queue Storage (transacciones) ---
echo "[7/11] Creando Queue '${QUEUE_NAME}'..."
az storage queue create \
  --account-name "${STORAGE_ACCOUNT}" \
  --name "${QUEUE_NAME}" \
  --auth-mode login \
  --output none

# --- Paso 7.5: Queue de documentos (módulo Jorge) ---
echo "[7.5] Creando Queue '${DOCUMENTS_QUEUE}'..."
az storage queue create \
  --account-name "${STORAGE_ACCOUNT}" \
  --name "${DOCUMENTS_QUEUE}" \
  --auth-mode login \
  --output none

# --- Paso 8: App Service Plan ---
echo "[8/11] Creando App Service Plan (SKU ${APP_SERVICE_SKU}, region ${APP_LOCATION})..."
az appservice plan create \
  --name "${APP_SERVICE_PLAN}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${APP_LOCATION}" \
  --sku "${APP_SERVICE_SKU}" \
  --is-linux \
  --output none

# --- Paso 9: App Service (Web App) ---
echo "[9/11] Creando Web App..."
az webapp create \
  --resource-group "${RESOURCE_GROUP}" \
  --plan "${APP_SERVICE_PLAN}" \
  --name "${WEBAPP}" \
  --runtime "PYTHON:3.12" \
  --output none

# --- Paso 10: Managed Identity ---
echo "[10/11] Asignando Managed Identity..."
az webapp identity assign \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${WEBAPP}" \
  --output none

PRINCIPAL_ID="$(az webapp identity show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${WEBAPP}" \
  --query principalId \
  --output tsv)"

echo "    principalId=${PRINCIPAL_ID}"
echo "${PRINCIPAL_ID}" > "${SCRIPT_DIR}/principal_id.txt"
echo "    Guardado en infra/principal_id.txt (compartir con Lukas)"

# --- Paso 11: App Settings (nombres alineados con la app) ---
echo "[11/11] Configurando variables de entorno..."
az webapp config appsettings set \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${WEBAPP}" \
  --settings \
    ENVIRONMENT=production \
    STORAGE_ACCOUNT="${STORAGE_ACCOUNT}" \
    BLOB_CONTAINER="${BLOB_CONTAINER}" \
    DOCUMENTS_QUEUE="${DOCUMENTS_QUEUE}" \
    QUEUE_NAME="${QUEUE_NAME}" \
    AUTH_ENABLED=true \
    KEY_VAULT_URL="https://${KEY_VAULT}.vault.azure.net/" \
  --output none

# --- Paso 12: Seguridad — Key Vault + RBAC (módulo Lukas) ---
echo "[12] Configurando Key Vault y RBAC de la Managed Identity..."
bash "${SCRIPT_DIR}/security.sh"

# --- Paso 13: Acceso privado — VNet integration + Private Endpoint ---
echo "[13] Configurando acceso privado del storage..."
bash "${SCRIPT_DIR}/private-network.sh" \
  || echo "  (omitido: requiere la VNet de Juanjo y App Service SKU B1+)"

# --- Paso 14: Budget + alertas de costo (módulo Chanti) ---
echo "[14] Configurando budget de costos..."
bash "${SCRIPT_DIR}/budget.sh" || echo "  (budget omitido)"

# --- Paso 15: Cosmos DB (NoSQL) — almacén de transacciones (módulo Chanti) ---
echo "[15] Desplegando Cosmos DB (NoSQL)..."
bash "${SCRIPT_DIR}/cosmos.sh" || echo "  (Cosmos omitido: revisar 'az login' y el free tier)"

echo
echo "==> Despliegue de infraestructura completado."
echo
echo "Resumen:"
echo "  RESOURCE_GROUP   = ${RESOURCE_GROUP}"
echo "  STORAGE_ACCOUNT  = ${STORAGE_ACCOUNT}"
echo "  BLOB_CONTAINER   = ${BLOB_CONTAINER}"
echo "  QUEUE_NAME       = ${QUEUE_NAME}"
echo "  COSMOS_ACCOUNT   = ${COSMOS_ACCOUNT} (NoSQL, pk ${COSMOS_PARTITION_KEY})"
echo "  WEBAPP           = ${WEBAPP}"
echo "  PRINCIPAL_ID     = ${PRINCIPAL_ID}"
echo "  URL              = https://${WEBAPP}.azurewebsites.net"
echo
echo "Siguiente (Paso 12, con Camila): desplegar el backend con"
echo "  az webapp up --resource-group \${RESOURCE_GROUP} --name \${WEBAPP} --runtime \"PYTHON:3.12\""
