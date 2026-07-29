#!/usr/bin/env bash
# =============================================================================
# CENTINELA — Despliegue en Azure Container Apps (Sprint 6, Fase 1)
# =============================================================================
# Lleva a Container Apps las dos cargas ya contenedorizadas:
#
#   ca-centinela-api-*     API de ingesta   — ingress público, escala por HTTP
#   ca-centinela-worker-*  motor de scoring — sin ingress, escala por KEDA según
#                                             la longitud de la cola
#
# NO toca el despliegue anterior (App Service + Function App): ambos conviven
# hasta validar los contenedores, y el checkpoint `pre-sprint6-funcional` sigue
# siendo el punto de retorno.
#
# Modelo de credenciales (regla dura del sprint: cero credenciales en repo,
# pipeline o imagen):
#   - Los secretos de aplicación viven en Key Vault y Container Apps los resuelve
#     con una Managed Identity de usuario. Nunca se escriben en claro aquí.
#   - El acceso a colas y Cosmos va por esa misma identidad y RBAC.
#   - El único secreto que hay que sembrar a mano es el token de PULL de GHCR
#     (GitHub no emite tokens de larga duración para terceros); también se guarda
#     en Key Vault y se referencia, no se pega en la línea de comandos.
#
# Prerrequisitos:
#   az login
#   export SUFFIX=sp5x1
#   # token con permiso read:packages, SOLO la primera vez:
#   export GHCR_PULL_TOKEN=ghp_xxx   export GHCR_USER=<tu-usuario-github>
#
# Uso:  bash infra/containerapps.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=variables.sh
source "${SCRIPT_DIR}/variables.sh"

echo "=========================================================="
echo " CENTINELA — Container Apps"
echo "   RG=${RESOURCE_GROUP}   Entorno=${ACA_ENVIRONMENT} (${ACA_LOCATION})"
echo "   API=${IMAGE_API}:${IMAGE_TAG}"
echo "   Worker=${IMAGE_WORKER}:${IMAGE_TAG}"
echo "=========================================================="

# --- 0. Providers ------------------------------------------------------------
echo "[1/8] Registrando providers..."
for NS in Microsoft.App Microsoft.OperationalInsights; do
  az provider register --namespace "${NS}" --wait --output none 2>/dev/null || true
done
az extension add --name containerapp --upgrade --only-show-errors --output none 2>/dev/null || true

# --- 1. Identidad gestionada de usuario --------------------------------------
# De usuario (no de sistema) para que API y worker compartan la MISMA identidad
# y baste un juego de asignaciones RBAC. Además sobrevive a recrear una app.
echo "[2/8] Identidad gestionada ${ACA_IDENTITY}..."
if ! az identity show -g "${RESOURCE_GROUP}" -n "${ACA_IDENTITY}" &>/dev/null; then
  az identity create -g "${RESOURCE_GROUP}" -n "${ACA_IDENTITY}" \
    --location "${ACA_LOCATION}" --output none
fi
IDENTITY_ID="$(az identity show -g "${RESOURCE_GROUP}" -n "${ACA_IDENTITY}" --query id -o tsv)"
IDENTITY_PRINCIPAL="$(az identity show -g "${RESOURCE_GROUP}" -n "${ACA_IDENTITY}" --query principalId -o tsv)"
IDENTITY_CLIENT_ID="$(az identity show -g "${RESOURCE_GROUP}" -n "${ACA_IDENTITY}" --query clientId -o tsv)"

# --- 2. RBAC de menor privilegio para esa identidad --------------------------
echo "[3/8] Asignando RBAC (colas, Key Vault, Cosmos)..."
KV_ID="$(az keyvault show -n "${KEY_VAULT}" -g "${RESOURCE_GROUP}" --query id -o tsv 2>/dev/null || true)"
SA_ID="$(az storage account show -g "${RESOURCE_GROUP}" -n "${STORAGE_ACCOUNT}" --query id -o tsv 2>/dev/null || true)"

assign_role() {  # rol, scope
  local role="$1" scope="$2"
  [[ -z "${scope}" ]] && return 0
  az role assignment create --assignee-object-id "${IDENTITY_PRINCIPAL}" \
    --assignee-principal-type ServicePrincipal \
    --role "${role}" --scope "${scope}" --output none 2>/dev/null || true
}
# La API publica en `transactions`; el worker lee de `transactions` y `cases` y
# publica en `cases`: ambas necesitan lectura y escritura de colas.
assign_role "Storage Queue Data Contributor" "${SA_ID}"
assign_role "Storage Blob Data Contributor"  "${SA_ID}"
assign_role "Key Vault Secrets User"         "${KV_ID}"

# --- 3. Token de pull de GHCR en Key Vault -----------------------------------
echo "[4/8] Acceso al registro (${REGISTRY_VISIBILITY})..."
# Con el paquete público, Container Apps hace pull anónimo: no hay credencial de
# registro que gestionar, ni en Key Vault ni en ninguna parte. Es el modelo con
# cero secretos persistentes.
REGISTRY_ARGS=()
REGISTRY_SECRETS=()
if [[ "${REGISTRY_VISIBILITY}" == "public" ]]; then
  echo "    paquete público: pull anónimo, sin credenciales."
elif [[ -n "${GHCR_PULL_TOKEN:-}" ]]; then
  # Se siembra por FICHERO, no con --value: un valor en la línea de comandos
  # queda visible en la lista de procesos de la máquina mientras dura el `az`.
  TOKEN_FILE="$(mktemp)"
  chmod 600 "${TOKEN_FILE}"
  printf '%s' "${GHCR_PULL_TOKEN}" >"${TOKEN_FILE}"
  az keyvault secret set --vault-name "${KEY_VAULT}" --name "${KV_SECRET_GHCR_TOKEN}" \
    --file "${TOKEN_FILE}" --output none
  rm -f "${TOKEN_FILE}"
  echo "    token guardado en Key Vault (secreto '${KV_SECRET_GHCR_TOKEN}')."
elif az keyvault secret show --vault-name "${KEY_VAULT}" --name "${KV_SECRET_GHCR_TOKEN}" &>/dev/null; then
  echo "    ya existe en Key Vault; se reutiliza."
else
  echo "    [ERROR] REGISTRY_VISIBILITY=private pero no hay token de pull."
  echo "            Crea un PAT con permiso 'read:packages' y exporta:"
  echo "            export GHCR_PULL_TOKEN=ghp_xxx GHCR_USER=<usuario>"
  echo "            O publica el paquete y usa REGISTRY_VISIBILITY=public (sin credenciales)."
  exit 1
fi

KV_URI="$(az keyvault show -n "${KEY_VAULT}" -g "${RESOURCE_GROUP}" --query properties.vaultUri -o tsv)"
kv_ref() { echo "${KV_URI}secrets/$1"; }

# Los flags de registro solo se añaden en modo privado. En público no se pasa
# ninguno: `az` no admite --registry-server sin credenciales asociadas.
if [[ "${REGISTRY_VISIBILITY}" != "public" ]]; then
  REGISTRY_ARGS=(
    --registry-server "${REGISTRY}"
    --registry-username "${GHCR_USER:-${REGISTRY_NAMESPACE}}"
    --registry-password "secretref:ghcr-token"
  )
  REGISTRY_SECRETS=(
    "ghcr-token=keyvaultref:$(kv_ref ${KV_SECRET_GHCR_TOKEN}),identityref:${IDENTITY_ID}"
  )
fi

# --- 3b. Comprobación previa: las imágenes tienen que existir ----------------
# Sin esto, Container Apps acepta el despliegue y crea una revisión que nunca
# arranca porque no puede hacer pull; el error solo se ve rebuscando en el
# portal. Ojo con `latest`: el pipeline SOLO la publica desde la rama por
# defecto, así que desplegando desde una rama de trabajo hay que indicar la
# etiqueta `sha-xxxxxxx` explícitamente.
if command -v docker &>/dev/null && [[ "${REGISTRY_VISIBILITY}" == "public" ]]; then
  echo "    Verificando que las imágenes existen en el registro..."
  for IMAGEN in "${IMAGE_API}:${IMAGE_TAG}" "${IMAGE_WORKER}:${IMAGE_TAG}"; do
    if ! docker manifest inspect "${IMAGEN}" >/dev/null 2>&1; then
      echo "    [ERROR] No se encuentra '${IMAGEN}'."
      echo "            Etiquetas disponibles: mira los paquetes del repositorio."
      echo "            Despliega una concreta con:  export IMAGE_TAG=sha-xxxxxxx"
      exit 1
    fi
  done
  echo "    ambas imágenes disponibles (${IMAGE_TAG})."
fi

# --- 4. Log Analytics --------------------------------------------------------
# Capa gratuita: 5 GB/mes de ingesta.
#
# Retención de 30 días, no menos: la SKU PerGB2018 rechaza cualquier valor por
# debajo ("RetentionInDays doesn't match the SKU limits"). Y da igual a efectos
# de coste, porque los primeros 31 días de retención no se cobran — bajarla no
# ahorraba nada.
echo "[5/8] Workspace de Log Analytics ${LOG_WORKSPACE}..."
if ! az monitor log-analytics workspace show -g "${RESOURCE_GROUP}" -n "${LOG_WORKSPACE}" &>/dev/null; then
  az monitor log-analytics workspace create \
    -g "${RESOURCE_GROUP}" -n "${LOG_WORKSPACE}" --location "${ACA_LOCATION}" \
    --retention-time 30 --output none
fi
LOG_ID="$(az monitor log-analytics workspace show -g "${RESOURCE_GROUP}" -n "${LOG_WORKSPACE}" \
  --query customerId -o tsv)"
LOG_KEY="$(az monitor log-analytics workspace get-shared-keys -g "${RESOURCE_GROUP}" -n "${LOG_WORKSPACE}" \
  --query primarySharedKey -o tsv)"

# --- 5. Entorno de Container Apps + agente OTel ------------------------------
echo "[6/8] Entorno ${ACA_ENVIRONMENT}..."
# Que el recurso EXISTA no significa que sirva. Un intento anterior que falló
# (p. ej. AKSCapacityHeavyUsage) deja el entorno creado pero inservible, y
# saltárselo por "ya existe" hace que el despliegue se quede girando sobre algo
# que nunca va a estar listo. Se comprueban las tres cosas: existencia, estado
# y región.
ENV_STATE="$(az containerapp env show -g "${RESOURCE_GROUP}" -n "${ACA_ENVIRONMENT}" \
  --query properties.provisioningState -o tsv 2>/dev/null || true)"
ENV_REGION="$(az containerapp env show -g "${RESOURCE_GROUP}" -n "${ACA_ENVIRONMENT}" \
  --query location -o tsv 2>/dev/null || true)"

if [[ -n "${ENV_STATE}" && "${ENV_STATE}" != "Succeeded" ]]; then
  echo "    [ERROR] El entorno existe pero está en estado '${ENV_STATE}' (región: ${ENV_REGION})."
  echo "            Suele ser el resto de un intento fallido. Bórralo y repite:"
  echo "              az containerapp env delete -g ${RESOURCE_GROUP} -n ${ACA_ENVIRONMENT} --yes"
  exit 1
fi

if [[ -n "${ENV_STATE}" ]]; then
  echo "    ya existe y está listo (${ENV_REGION})."
  if [[ "${ENV_REGION// /}" != "${ACA_LOCATION}" ]]; then
    echo "    [AVISO] está en ${ENV_REGION}, no en ${ACA_LOCATION}. Se reutiliza tal cual;"
    echo "            para moverlo hay que borrarlo y recrearlo."
  fi
else
  az containerapp env create \
    -g "${RESOURCE_GROUP}" -n "${ACA_ENVIRONMENT}" --location "${ACA_LOCATION}" \
    --logs-workspace-id "${LOG_ID}" --logs-workspace-key "${LOG_KEY}" \
    --output none
fi

# Agente OTel gestionado del entorno: recibe OTLP de los contenedores y lo
# reenvía a Application Insights. Con esto la aplicación no necesita ninguna
# clave de instrumentación dentro de la imagen: solo habla con localhost.
APPINSIGHTS_CONN=""
if az extension show --name application-insights &>/dev/null || \
   az extension add --name application-insights --only-show-errors --output none 2>/dev/null; then
  if ! az monitor app-insights component show -g "${RESOURCE_GROUP}" -a "appi-${PROJECT}-${ENV}${SUFFIX:+-${SUFFIX}}" &>/dev/null; then
    az monitor app-insights component create \
      -g "${RESOURCE_GROUP}" -a "appi-${PROJECT}-${ENV}${SUFFIX:+-${SUFFIX}}" \
      --location "${ACA_LOCATION}" --workspace "${LOG_WORKSPACE}" --output none 2>/dev/null || true
  fi
  APPINSIGHTS_CONN="$(az monitor app-insights component show \
    -g "${RESOURCE_GROUP}" -a "appi-${PROJECT}-${ENV}${SUFFIX:+-${SUFFIX}}" \
    --query connectionString -o tsv 2>/dev/null || true)"
fi
if [[ -n "${APPINSIGHTS_CONN}" ]]; then
  az containerapp env telemetry app-insights set \
    -g "${RESOURCE_GROUP}" -n "${ACA_ENVIRONMENT}" \
    --connection-string "${APPINSIGHTS_CONN}" \
    --enable-open-telemetry-traces true --enable-open-telemetry-logs true \
    --output none 2>/dev/null || \
    echo "    [AVISO] no se pudo activar el agente OTel; la app seguirá sin exportar trazas."
fi

# --- 6. API (ingress público, escala por HTTP) -------------------------------
echo "[7/8] Container App de la API..."
COSMOS_ENDPOINT="$(az cosmosdb show -n "${COSMOS_ACCOUNT}" -g "${RESOURCE_GROUP}" \
  --query documentEndpoint -o tsv 2>/dev/null || true)"

API_ENV_VARS=(
  "COSMOS_ENDPOINT=${COSMOS_ENDPOINT}"
  "COSMOS_DATABASE=${COSMOS_DATABASE}"
  "COSMOS_CONTAINER=${COSMOS_CONTAINER}"
  "STORAGE_ACCOUNT=${STORAGE_ACCOUNT}"
  "TRANSACTIONS_QUEUE=${QUEUE_NAME}"
  "CASES_QUEUE=${CASES_QUEUE}"
  "DOCUMENTS_QUEUE=${DOCUMENTS_QUEUE}"
  "BLOB_CONTAINER=${BLOB_CONTAINER}"
  "AUTH_ENABLED=true"
  "ENVIRONMENT=${ENV}"
  # DefaultAzureCredential debe elegir ESTA identidad de usuario, no otra.
  "AZURE_CLIENT_ID=${IDENTITY_CLIENT_ID}"
  # Los secretos entran como referencia al secreto de la app, jamás con su valor.
  "COSMOS_KEY=secretref:cosmos-key"
  "CASES_DB_DSN=secretref:cases-db-dsn"
  "API_KEYS=secretref:api-keys"
)

if ! az containerapp show -g "${RESOURCE_GROUP}" -n "${ACA_API}" &>/dev/null; then
  az containerapp create \
    -g "${RESOURCE_GROUP}" -n "${ACA_API}" --environment "${ACA_ENVIRONMENT}" \
    --image "${IMAGE_API}:${IMAGE_TAG}" \
    --user-assigned "${IDENTITY_ID}" \
    "${REGISTRY_ARGS[@]+"${REGISTRY_ARGS[@]}"}" \
    --secrets \
      "${REGISTRY_SECRETS[@]+"${REGISTRY_SECRETS[@]}"}" \
      "cosmos-key=keyvaultref:$(kv_ref ${KV_SECRET_COSMOS_KEY}),identityref:${IDENTITY_ID}" \
      "cases-db-dsn=keyvaultref:$(kv_ref ${KV_SECRET_CASES_DSN}),identityref:${IDENTITY_ID}" \
      "api-keys=keyvaultref:$(kv_ref ${KV_SECRET_API_KEYS}),identityref:${IDENTITY_ID}" \
    --env-vars "${API_ENV_VARS[@]}" \
    --target-port 8000 --ingress external \
    --cpu "${ACA_CPU}" --memory "${ACA_MEMORY}" \
    --min-replicas "${ACA_API_MIN_REPLICAS}" --max-replicas "${ACA_API_MAX_REPLICAS}" \
    --output none
else
  az containerapp update -g "${RESOURCE_GROUP}" -n "${ACA_API}" \
    --image "${IMAGE_API}:${IMAGE_TAG}" \
    --set-env-vars "${API_ENV_VARS[@]}" \
    --min-replicas "${ACA_API_MIN_REPLICAS}" --max-replicas "${ACA_API_MAX_REPLICAS}" \
    --output none
fi

# Sondas: liveness reinicia el contenedor si el proceso se cuelga; readiness lo
# saca del balanceo mientras arranca, para que no reciba tráfico a medio iniciar.
#
# `az containerapp create/update` NO tiene flags de probe en ninguna versión de
# la extensión, así que se parchea el YAML de la app: se descarga, se inyectan
# las sondas en el contenedor y se vuelve a aplicar.
echo "    Aplicando sondas de salud..."
# Se trabaja en JSON, no en YAML: `--yaml` acepta JSON (YAML es un superconjunto)
# y así el parcheo usa el módulo `json` de la stdlib en vez de exigir PyYAML
# instalado en la máquina que despliega.
APP_SPEC="$(mktemp -d)/api.json"
az containerapp show -g "${RESOURCE_GROUP}" -n "${ACA_API}" -o json >"${APP_SPEC}"
python3 - "${APP_SPEC}" <<'PATCH_PROBES'
import json
import sys

path = sys.argv[1]
with open(path) as handle:
    app = json.load(handle)

containers = app.get("properties", {}).get("template", {}).get("containers", [])
if not containers:
    sys.exit(4)

containers[0]["probes"] = [
    {
        # Liveness: solo confirma que el proceso responde. A propósito NO mira
        # Cosmos ni PostgreSQL: si lo hiciera, una caída de la base reiniciaría
        # en bucle un contenedor que está perfectamente sano.
        "type": "Liveness",
        "httpGet": {"path": "/health", "port": 8000},
        "initialDelaySeconds": 10,
        "periodSeconds": 30,
        "failureThreshold": 3,
    },
    {
        "type": "Readiness",
        "httpGet": {"path": "/health/ready", "port": 8000},
        "initialDelaySeconds": 3,
        "periodSeconds": 10,
        "failureThreshold": 3,
    },
]

with open(path, "w") as handle:
    json.dump(app, handle)
PATCH_PROBES
PATCH_STATUS=$?

if [[ ${PATCH_STATUS} -eq 0 ]]; then
  az containerapp update -g "${RESOURCE_GROUP}" -n "${ACA_API}" \
    --yaml "${APP_SPEC}" --output none && echo "    sondas aplicadas." || \
    echo "    [AVISO] no se pudieron aplicar las sondas; la app funciona con las de por defecto."
else
  echo "    [AVISO] no se pudo parchear la especificación; sondas omitidas."
fi

# --- 7. Worker (sin ingress, escala por longitud de cola) --------------------
# El worker no expone puerto: para eso NO se pasa `--ingress`. No existe un
# valor "disabled" —la CLI solo acepta internal|external— y omitir el flag es
# la forma correcta de dejar la app sin entrada de red.
echo "[8/8] Container App del worker..."
# Verificación documental (Fase 2): si el recurso de OCR existe, el worker
# recibe su endpoint y verifica; si no, cae al analizador nulo y solo vincula el
# documento al caso. Sin clave: se autentica con la Managed Identity.
DI_ENDPOINT="$(az cognitiveservices account show -g "${RESOURCE_GROUP}" \
  -n "${DOC_INTELLIGENCE}" --query properties.endpoint -o tsv 2>/dev/null || true)"
if [[ -z "${DI_ENDPOINT}" ]]; then
  echo "    [AVISO] Document Intelligence no aprovisionado; el worker registrará"
  echo "            los documentos sin verificarlos. Créalo con:"
  echo "            bash infra/document-intelligence.sh"
fi

WORKER_ENV_VARS=(
  "COSMOS_ENDPOINT=${COSMOS_ENDPOINT}"
  "COSMOS_DATABASE=${COSMOS_DATABASE}"
  "COSMOS_CONTAINER=${COSMOS_CONTAINER}"
  "STORAGE_ACCOUNT=${STORAGE_ACCOUNT}"
  "TRANSACTIONS_QUEUE=${QUEUE_NAME}"
  "CASES_QUEUE=${CASES_QUEUE}"
  "DOCUMENTS_QUEUE=${DOCUMENTS_QUEUE}"
  "EXPLANATIONS_QUEUE=${EXPLANATIONS_QUEUE}"
  "BLOB_CONTAINER=${BLOB_CONTAINER}"
  "DOC_INTELLIGENCE_ENDPOINT=${DI_ENDPOINT}"
  "DOC_INTELLIGENCE_MODEL=${DOC_INTELLIGENCE_MODEL}"
  "ENVIRONMENT=${ENV}"
  "AZURE_CLIENT_ID=${IDENTITY_CLIENT_ID}"
  "COSMOS_KEY=secretref:cosmos-key"
  "CASES_DB_DSN=secretref:cases-db-dsn"
)

if ! az containerapp show -g "${RESOURCE_GROUP}" -n "${ACA_WORKER}" &>/dev/null; then
  az containerapp create \
    -g "${RESOURCE_GROUP}" -n "${ACA_WORKER}" --environment "${ACA_ENVIRONMENT}" \
    --image "${IMAGE_WORKER}:${IMAGE_TAG}" \
    --user-assigned "${IDENTITY_ID}" \
    "${REGISTRY_ARGS[@]+"${REGISTRY_ARGS[@]}"}" \
    --secrets \
      "${REGISTRY_SECRETS[@]+"${REGISTRY_SECRETS[@]}"}" \
      "cosmos-key=keyvaultref:$(kv_ref ${KV_SECRET_COSMOS_KEY}),identityref:${IDENTITY_ID}" \
      "cases-db-dsn=keyvaultref:$(kv_ref ${KV_SECRET_CASES_DSN}),identityref:${IDENTITY_ID}" \
    --env-vars "${WORKER_ENV_VARS[@]}" \
    --cpu "${ACA_CPU}" --memory "${ACA_MEMORY}" \
    --min-replicas "${ACA_WORKER_MIN_REPLICAS}" --max-replicas "${ACA_WORKER_MAX_REPLICAS}" \
    --output none
else
  az containerapp update -g "${RESOURCE_GROUP}" -n "${ACA_WORKER}" \
    --image "${IMAGE_WORKER}:${IMAGE_TAG}" \
    --set-env-vars "${WORKER_ENV_VARS[@]}" \
    --min-replicas "${ACA_WORKER_MIN_REPLICAS}" --max-replicas "${ACA_WORKER_MAX_REPLICAS}" \
    --output none
fi

# Regla KEDA: una réplica más por cada ACA_QUEUE_LENGTH mensajes pendientes.
# La autenticación del scaler va por la misma Managed Identity, así que tampoco
# aquí hace falta una connection string de storage.
for QUEUE in "${QUEUE_NAME}" "${CASES_QUEUE}" "${DOCUMENTS_QUEUE}" "${EXPLANATIONS_QUEUE}"; do
  az containerapp update -g "${RESOURCE_GROUP}" -n "${ACA_WORKER}" \
    --scale-rule-name "${QUEUE}-scaler" \
    --scale-rule-type azure-queue \
    --scale-rule-metadata "accountName=${STORAGE_ACCOUNT}" "queueName=${QUEUE}" \
                          "queueLength=${ACA_QUEUE_LENGTH}" \
    --scale-rule-identity "${IDENTITY_ID}" \
    --output none 2>/dev/null || \
    echo "    [AVISO] no se pudo aplicar la regla de escalado para '${QUEUE}'."
done

# --- Resumen -----------------------------------------------------------------
API_FQDN="$(az containerapp show -g "${RESOURCE_GROUP}" -n "${ACA_API}" \
  --query properties.configuration.ingress.fqdn -o tsv 2>/dev/null || true)"

echo
echo "=========================================================="
echo " Despliegue en Container Apps completado"
echo "=========================================================="
echo "  API:    https://${API_FQDN}"
echo "  Worker: ${ACA_WORKER} (escala 0→${ACA_WORKER_MAX_REPLICAS} por longitud de cola)"
echo
echo "  Salud:      curl https://${API_FQDN}/health"
echo "  Adaptadores: curl https://${API_FQDN}/health/ready"
echo "  Logs worker: az containerapp logs show -g ${RESOURCE_GROUP} -n ${ACA_WORKER} --follow"
echo
echo "  El despliegue anterior (App Service + Function App) sigue intacto."
echo "  Punto de retorno: git checkout pre-sprint6-funcional"
