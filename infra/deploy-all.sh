#!/usr/bin/env bash
# =============================================================================
# CENTINELA — Despliegue END-TO-END en una sola corrida (módulo Jorge, Semana 4)
# =============================================================================
# Orquesta TODO el sistema en Azure, con los ajustes aprendidos en el despliegue
# real: nombres globales únicos (SUFFIX), región de Cosmos con cupo, creación de
# la Function App (worker), y secretos cableados por referencia a Key Vault.
#
# Prerrequisitos:
#   - az login  (rol Owner o Contributor + User Access Administrator para RBAC)
#   - func      (Azure Functions Core Tools v4)  — para publicar el worker
#   - zip, curl, openssl
#
# Secretos: se toman de variables de entorno; si no se definen, se generan para
# la demo. NUNCA se versionan (los guarda Key Vault vía security.sh).
#
# Uso:
#   export SUFFIX=ab12cd            # único si hay colisión de nombres (recomendado)
#   bash infra/deploy-all.sh
#
# Al terminar, validar el cierre con:  docs/deployment-guide.md
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=variables.sh
source "${SCRIPT_DIR}/variables.sh"
BACKEND_DIR="${SCRIPT_DIR}/../backend"

echo "=========================================================="
echo " Despliegue end-to-end de CENTINELA"
echo "   RG=${RESOURCE_GROUP}  WebApp=${WEBAPP}  Func=${FUNCTION_APP}"
echo "   Cosmos=${COSMOS_ACCOUNT} (${COSMOS_LOCATION})  PG=${DB_SERVER}"
echo "=========================================================="

# --- Fase 1: infra base + Key Vault + Cosmos (deploy.sh + cosmos.sh) ----------
echo "[1/7] Infraestructura base (storage, colas, Web App, Managed Identity, Key Vault, Cosmos)..."
bash "${SCRIPT_DIR}/deploy.sh"

# --- Fase 2: PostgreSQL (modo DEMO: público con firewall) --------------------
# NOTA: el diseño de PRODUCCIÓN es PRIVADO (deploy-cases-db.sh sobre VNet). Con
# App Service F1 (sin integración VNet) la BD privada no es alcanzable, así que
# para la demo end-to-end se usa acceso público + firewall. En producción se sube
# a App Service B1+ con VNet y se usa el script privado.
echo "[2/7] PostgreSQL (modo demo: público con firewall)..."
# El provider de PostgreSQL debe estar registrado (deploy.sh registra storage/web/
# cosmos, pero NO éste). Sin esto falla con MissingSubscriptionRegistration.
az provider register --namespace Microsoft.DBforPostgreSQL --wait --output none 2>/dev/null || true
DB_ADMIN_PASS="${DB_ADMIN_PASS:-Centinela$(openssl rand -hex 6)!}"
if ! az postgres flexible-server show -g "${RESOURCE_GROUP}" -n "${DB_SERVER}" &>/dev/null; then
  az postgres flexible-server create \
    --resource-group "${RESOURCE_GROUP}" --name "${DB_SERVER}" \
    --location "${DB_LOCATION}" \
    --admin-user "${DB_ADMIN_USER}" --admin-password "${DB_ADMIN_PASS}" \
    --sku-name Standard_B1ms --tier Burstable --storage-size 32 --version 16 \
    --public-access 0.0.0.0 --yes --output none
else
  echo "    Servidor PostgreSQL '${DB_SERVER}' ya existe."
fi
# Permitir la IP del desplegador para aplicar el DDL desde esta máquina.
MYIP="$(curl -s ifconfig.me || true)"
if [[ -n "${MYIP}" ]]; then
  # OJO sintaxis: la regla usa --server-name (no -n) y --name para el nombre de
  # la regla (no --rule-name). Con la sintaxis vieja la regla nunca se creaba y
  # el DDL fallaba con "Operation timed out".
  az postgres flexible-server firewall-rule create \
    --resource-group "${RESOURCE_GROUP}" --server-name "${DB_SERVER}" --name allow-deployer \
    --start-ip-address "${MYIP}" --end-ip-address "${MYIP}" --output none || \
    echo "    [AVISO] No se pudo crear la regla de firewall para la IP del desplegador."
fi
az postgres flexible-server db create \
  -g "${RESOURCE_GROUP}" -s "${DB_SERVER}" -d "${DB_NAME}" --output none 2>/dev/null || true

# DSN de conexión (contiene el password → es SECRETO, va a Key Vault en la fase 5).
CASES_DB_DSN="postgresql://${DB_ADMIN_USER}:${DB_ADMIN_PASS}@${DB_SERVER}.postgres.database.azure.com:5432/${DB_NAME}?sslmode=require"

# Aplicar el DDL (modo local por DSN — script de Juan José).
echo "    Aplicando DDL de la base de casos..."
CASES_DB_DSN="${CASES_DB_DSN}" bash "${SCRIPT_DIR}/deploy-cases-db.sh" || \
  echo "    [AVISO] No se pudo aplicar el DDL automáticamente; aplícalo con: psql \"\${CASES_DB_DSN}\" -f scripts/init-cases-db.sql"

# --- Fase 3: Function App (worker) -------------------------------------------
echo "[3/7] Function App (worker de scoring + consumidor de casos)..."
if ! az functionapp show -g "${RESOURCE_GROUP}" -n "${FUNCTION_APP}" &>/dev/null; then
  az functionapp create \
    --resource-group "${RESOURCE_GROUP}" --name "${FUNCTION_APP}" \
    --storage-account "${STORAGE_ACCOUNT}" --consumption-plan-location "${LOCATION}" \
    --runtime python --runtime-version 3.12 --functions-version 4 \
    --os-type Linux --output none
  az functionapp identity assign -g "${RESOURCE_GROUP}" -n "${FUNCTION_APP}" --output none
else
  echo "    Function App '${FUNCTION_APP}' ya existe."
fi

# --- Fase 4: datos de Cosmos (endpoint + clave) ------------------------------
echo "[4/7] Obteniendo endpoint y clave de Cosmos..."
COSMOS_ENDPOINT="$(az cosmosdb show -n "${COSMOS_ACCOUNT}" -g "${RESOURCE_GROUP}" --query documentEndpoint -o tsv)"
COSMOS_KEY="$(az cosmosdb keys list -n "${COSMOS_ACCOUNT}" -g "${RESOURCE_GROUP}" --query primaryMasterKey -o tsv)"

# --- Fase 5: secretos en Key Vault + referencias (security.sh de Lukas) ------
echo "[5/7] Guardando secretos en Key Vault y cableando referencias..."
export COSMOS_KEY CASES_DB_DSN DB_ADMIN_PASS FUNCTION_APP
bash "${SCRIPT_DIR}/security.sh"

# --- Fase 6: app settings (no-secretos) + despliegue de código ---------------
echo "[6/7] Configurando app settings y desplegando código..."
# Ajustes no-secretos (endpoint/config) en Web App y Function App.
for TARGET in "webapp:${WEBAPP}" "functionapp:${FUNCTION_APP}"; do
  KIND="${TARGET%%:*}"; NAME="${TARGET##*:}"
  # STORAGE_ACCOUNT es OBLIGATORIO en la Function App: sin él, el worker cae a la
  # cola de casos EN MEMORIA (los casos nunca llegan a persist_case).
  az "${KIND}" config appsettings set -g "${RESOURCE_GROUP}" -n "${NAME}" --settings \
    COSMOS_ENDPOINT="${COSMOS_ENDPOINT}" \
    COSMOS_DATABASE="${COSMOS_DATABASE}" \
    COSMOS_CONTAINER="${COSMOS_CONTAINER}" \
    STORAGE_ACCOUNT="${STORAGE_ACCOUNT}" \
    CASES_QUEUE="${CASES_QUEUE}" \
    AUTH_ENABLED=true \
    SCM_DO_BUILD_DURING_DEPLOYMENT=true ENABLE_ORYX_BUILD=true \
    --output none
done

# El worker publica en la cola `cases` por Managed Identity: su identidad necesita
# el rol de escritura de colas en el storage (sin secretos). Idempotente.
FUNC_MI="$(az functionapp identity show -g "${RESOURCE_GROUP}" -n "${FUNCTION_APP}" --query principalId -o tsv 2>/dev/null || true)"
SA_ID="$(az storage account show -g "${RESOURCE_GROUP}" -n "${STORAGE_ACCOUNT}" --query id -o tsv 2>/dev/null || true)"
if [[ -n "${FUNC_MI}" && -n "${SA_ID}" ]]; then
  az role assignment create --assignee-object-id "${FUNC_MI}" \
    --assignee-principal-type ServicePrincipal \
    --role "Storage Queue Data Contributor" --scope "${SA_ID}" --output none 2>/dev/null || true
fi
# Startup de la API (FastAPI/uvicorn).
az webapp config set -g "${RESOURCE_GROUP}" -n "${WEBAPP}" \
  --startup-file "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000" --output none

# Empaquetar el backend (sin el entorno virtual local).
DEPLOY_ZIP="$(mktemp -d)/centinela.zip"
( cd "${BACKEND_DIR}" && zip -qr "${DEPLOY_ZIP}" . \
    -x ".venv/*" -x "*/__pycache__/*" -x ".pytest_cache/*" -x "__pycache__/*" )

# Desplegar la API (Web App).
echo "    Desplegando la API..."
az webapp deploy -g "${RESOURCE_GROUP}" -n "${WEBAPP}" --src-path "${DEPLOY_ZIP}" --type zip

# Desplegar el worker (Function App). config-zip no registra bien en Consumption
# Python; se usa 'func' (Core Tools), que hace el build remoto correctamente.
echo "    Desplegando el worker..."
if command -v func &>/dev/null; then
  ( cd "${BACKEND_DIR}" && func azure functionapp publish "${FUNCTION_APP}" --python )
else
  echo "    [AVISO] 'func' no está instalado. Publica el worker manualmente:"
  echo "            cd backend && func azure functionapp publish ${FUNCTION_APP} --python"
fi

# --- Fase 7: resumen ---------------------------------------------------------
echo "[7/7] Despliegue completado."
echo
echo "  API:    https://${WEBAPP}.azurewebsites.net"
echo "  Worker: ${FUNCTION_APP} (score_transaction + persist_case)"
echo "  Cosmos: ${COSMOS_ACCOUNT}   PostgreSQL: ${DB_SERVER}"
echo
echo "  Validación de cierre (transacción → caso → GET /cases): docs/deployment-guide.md"
echo "  Verificar secretos:  bash infra/verify_secrets.sh"
echo "  Apagar todo:         bash infra/destroy.sh"
