#!/usr/bin/env bash
# Seguridad (módulo Lukas): Key Vault + RBAC a la Managed Identity.
#
# Requiere: RG, Storage Account y Web App ya creados (deploy.sh) + az login.
# Modela el principio de menor privilegio: la identidad de la app solo
# obtiene acceso a datos de blob/queue y a leer secretos del Key Vault.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=variables.sh
source "${SCRIPT_DIR}/variables.sh"

echo "==> Creando Key Vault ${KEY_VAULT} (RBAC authorization)..."
az keyvault create \
  --name "${KEY_VAULT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --enable-rbac-authorization true \
  --output none

# principalId de la Managed Identity de la Web App
if [[ -f "${SCRIPT_DIR}/principal_id.txt" ]]; then
  PRINCIPAL_ID="$(cat "${SCRIPT_DIR}/principal_id.txt")"
else
  PRINCIPAL_ID="$(az webapp identity show \
    --resource-group "${RESOURCE_GROUP}" --name "${WEBAPP}" \
    --query principalId -o tsv)"
fi
echo "    principalId=${PRINCIPAL_ID}"

STORAGE_ID="$(az storage account show \
  --resource-group "${RESOURCE_GROUP}" --name "${STORAGE_ACCOUNT}" \
  --query id -o tsv)"
KV_ID="$(az keyvault show --name "${KEY_VAULT}" --query id -o tsv)"

echo "==> Asignando roles RBAC (menor privilegio)..."
az role assignment create --assignee-object-id "${PRINCIPAL_ID}" \
  --assignee-principal-type ServicePrincipal \
  --role "Storage Blob Data Contributor" --scope "${STORAGE_ID}" --output none
az role assignment create --assignee-object-id "${PRINCIPAL_ID}" \
  --assignee-principal-type ServicePrincipal \
  --role "Storage Queue Data Contributor" --scope "${STORAGE_ID}" --output none
az role assignment create --assignee-object-id "${PRINCIPAL_ID}" \
  --assignee-principal-type ServicePrincipal \
  --role "Key Vault Secrets User" --scope "${KV_ID}" --output none

echo "==> Guardando las API keys de la app como secreto (roles de negocio)..."
echo "    Ajustar los valores reales; NUNCA versionar claves en git."
az keyvault secret set --vault-name "${KEY_VAULT}" --name "api-keys" \
  --value "${API_KEYS:-svc-key:servicio,adm-key:administrador}" --output none

echo "==> Seguridad configurada (Key Vault + RBAC)."
