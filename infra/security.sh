#!/usr/bin/env bash
# Seguridad (módulo Lukas, Semana 4): Key Vault idempotente, permisos
# automáticos y secretos consumidos POR REFERENCIA (nunca en claro).
#
# - Re-ejecutable: no falla si el Key Vault, los roles o los secretos ya existen.
# - Sin pasos manuales: otorga al usuario que despliega el permiso de datos del
#   vault automáticamente (Key Vault Secrets Officer).
# - Los VALORES de los secretos se toman de variables de entorno; NUNCA se
#   versionan en el repositorio:
#     export API_KEYS="svc-key:servicio,adm-key:administrador"
#     export COSMOS_KEY="<clave-cosmos>"
#     export CASES_DB_DSN="postgresql://user:pass@host:5432/centinela_cases?sslmode=require"
#     export DB_ADMIN_PASS="<password-postgres>"
#
# Requiere: RG + Web App ya creados (deploy.sh) + az login.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=variables.sh
source "${SCRIPT_DIR}/variables.sh"

# ---------------------------------------------------------------------------
# 1. Key Vault (idempotente: se reutiliza si ya existe)
# ---------------------------------------------------------------------------
if az keyvault show --name "${KEY_VAULT}" --resource-group "${RESOURCE_GROUP}" &>/dev/null; then
  echo "==> Key Vault ${KEY_VAULT} ya existe. Se reutiliza."
else
  echo "==> Creando Key Vault ${KEY_VAULT} (RBAC authorization)..."
  az keyvault create \
    --name "${KEY_VAULT}" \
    --resource-group "${RESOURCE_GROUP}" \
    --location "${LOCATION}" \
    --enable-rbac-authorization true \
    --output none
fi

KV_ID="$(az keyvault show --name "${KEY_VAULT}" --query id -o tsv)"

# ---------------------------------------------------------------------------
# 2. Permiso del USUARIO que despliega (automático, sin pasos manuales)
#    En un vault con RBAC, crear el vault NO otorga permiso de datos: hay que
#    asignar 'Key Vault Secrets Officer' para poder escribir secretos.
# ---------------------------------------------------------------------------
DEPLOYER_OID="$(az ad signed-in-user show --query id -o tsv 2>/dev/null || true)"
if [[ -n "${DEPLOYER_OID}" ]]; then
  echo "==> Otorgando 'Key Vault Secrets Officer' al usuario que despliega..."
  az role assignment create \
    --assignee-object-id "${DEPLOYER_OID}" \
    --assignee-principal-type User \
    --role "Key Vault Secrets Officer" \
    --scope "${KV_ID}" \
    --output none 2>/dev/null || echo "    (rol ya asignado)"
  echo "    Esperando propagación de RBAC..."
  sleep 20
else
  echo "==> [AVISO] No se pudo resolver el usuario actual (az ad signed-in-user)."
  echo "    Asegúrate de tener 'Key Vault Secrets Officer' sobre ${KEY_VAULT}."
fi

# ---------------------------------------------------------------------------
# 3. Managed Identity de la Web App: roles de datos (menor privilegio).
#    'Key Vault Secrets User' permite RESOLVER las referencias @Microsoft.KeyVault.
# ---------------------------------------------------------------------------
if [[ -f "${SCRIPT_DIR}/principal_id.txt" ]]; then
  PRINCIPAL_ID="$(cat "${SCRIPT_DIR}/principal_id.txt")"
else
  PRINCIPAL_ID="$(az webapp identity show \
    --resource-group "${RESOURCE_GROUP}" --name "${WEBAPP}" \
    --query principalId -o tsv)"
fi
echo "==> Managed Identity de la Web App: ${PRINCIPAL_ID}"

STORAGE_ID="$(az storage account show \
  --resource-group "${RESOURCE_GROUP}" --name "${STORAGE_ACCOUNT}" \
  --query id -o tsv)"

assign_role() {  # rol, scope — idempotente
  local role="$1" scope="$2"
  az role assignment create \
    --assignee-object-id "${PRINCIPAL_ID}" \
    --assignee-principal-type ServicePrincipal \
    --role "${role}" --scope "${scope}" --output none 2>/dev/null \
    || echo "    (rol '${role}' ya asignado)"
}
echo "==> Asignando roles RBAC de menor privilegio a la Managed Identity..."
assign_role "Storage Blob Data Contributor" "${STORAGE_ID}"
assign_role "Storage Queue Data Contributor" "${STORAGE_ID}"
assign_role "Key Vault Secrets User" "${KV_ID}"

# ---------------------------------------------------------------------------
# 4. Secretos en Key Vault (valores desde variables de entorno; nunca en git)
# ---------------------------------------------------------------------------
upsert_secret() {  # nombre, valor, nombre-de-variable-para-el-aviso
  local name="$1" value="$2" hint="$3"
  if [[ -z "${value}" ]]; then
    echo "    [AVISO] Secreto '${name}' sin valor (exporta ${hint}). Se omite."
    return 0
  fi
  az keyvault secret set --vault-name "${KEY_VAULT}" --name "${name}" \
    --value "${value}" --output none
  echo "    secreto '${name}' guardado."
}
echo "==> Guardando secretos en Key Vault (desde el entorno)..."
upsert_secret "api-keys"          "${API_KEYS:-svc-key:servicio,adm-key:administrador}" "API_KEYS"
upsert_secret "cosmos-db-key"     "${COSMOS_KEY:-}"    "COSMOS_KEY"
upsert_secret "cases-db-dsn"      "${CASES_DB_DSN:-}"  "CASES_DB_DSN"
upsert_secret "db-admin-password" "${DB_ADMIN_PASS:-}" "DB_ADMIN_PASS"

# ---------------------------------------------------------------------------
# 5. App settings POR REFERENCIA a Key Vault (nunca el valor en claro).
#    La Web App resuelve @Microsoft.KeyVault con su Managed Identity.
# ---------------------------------------------------------------------------
kv_ref() { echo "@Microsoft.KeyVault(VaultName=${KEY_VAULT};SecretName=$1)"; }

echo "==> Configurando app settings de ${WEBAPP} por referencia a Key Vault..."
az webapp config appsettings set \
  --resource-group "${RESOURCE_GROUP}" --name "${WEBAPP}" \
  --settings \
    COSMOS_KEY="$(kv_ref cosmos-db-key)" \
    CASES_DB_DSN="$(kv_ref cases-db-dsn)" \
  --output none

# Opcional: si existe una Function App (worker), aplicarle las mismas referencias.
if [[ -n "${FUNCTION_APP:-}" ]] && \
   az functionapp show -g "${RESOURCE_GROUP}" -n "${FUNCTION_APP}" &>/dev/null; then
  echo "==> Aplicando referencias a la Function App ${FUNCTION_APP}..."
  FUNC_OID="$(az functionapp identity show -g "${RESOURCE_GROUP}" -n "${FUNCTION_APP}" \
    --query principalId -o tsv 2>/dev/null || true)"
  if [[ -n "${FUNC_OID}" ]]; then
    az role assignment create --assignee-object-id "${FUNC_OID}" \
      --assignee-principal-type ServicePrincipal \
      --role "Key Vault Secrets User" --scope "${KV_ID}" --output none 2>/dev/null || true
  fi
  az functionapp config appsettings set -g "${RESOURCE_GROUP}" -n "${FUNCTION_APP}" \
    --settings \
      COSMOS_KEY="$(kv_ref cosmos-db-key)" \
      CASES_DB_DSN="$(kv_ref cases-db-dsn)" \
    --output none
fi

echo
echo "==> Seguridad configurada: Key Vault idempotente, permisos automáticos"
echo "    y secretos consumidos por referencia (sin valores en claro)."
echo "    Verifica con: bash infra/verify_secrets.sh"
