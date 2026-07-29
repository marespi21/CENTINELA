#!/usr/bin/env bash
# =============================================================================
# CENTINELA — Identidad federada GitHub → Azure (Sprint 6, Fase 5)
# =============================================================================
# Configura OIDC para que el pipeline despliegue en Azure **sin ningún secreto
# almacenado**. GitHub emite un token de vida corta por ejecución y Entra ID lo
# canjea comprobando de qué repositorio, rama o entorno viene.
#
# Sustituye a `secrets.AZURE_CREDENTIALS`, que es un service principal con
# clientSecret guardado en GitHub: un secreto de larga duración, con permisos
# sobre la suscripción, que no caduca solo y que cualquiera con acceso de
# escritura al repo puede usar desde un workflow.
#
# Diferencia práctica:
#   AZURE_CREDENTIALS  → si se filtra, sirve hasta que alguien la revoque
#   OIDC               → no hay nada que filtrar; el token vive minutos y solo
#                        vale para el repo/entorno declarado en la federación
#
# Los tres valores que imprime al final NO son secretos: son identificadores
# públicos. Van como *variables* del repositorio, no como secrets.
#
# Requisitos: permiso para registrar aplicaciones en Entra ID y para asignar
# roles en el grupo de recursos.
#
# Uso:  export SUFFIX=sp5x1 && bash infra/github-oidc.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=variables.sh
source "${SCRIPT_DIR}/variables.sh"

GITHUB_REPO="${GITHUB_REPO:-marespi21/CENTINELA}"
APP_NAME="${APP_NAME:-gh-${PROJECT}-${ENV}-deploy}"
# Entornos de GitHub sobre los que se autoriza el despliegue. El gate de
# aprobación se configura en GitHub sobre estos mismos nombres.
ENVIRONMENTS=("dev" "prod")
# Ramas autorizadas a desplegar sin pasar por un entorno.
BRANCHES=("develop" "main")

echo "=========================================================="
echo " OIDC GitHub → Azure"
echo "   Repo:  ${GITHUB_REPO}"
echo "   App:   ${APP_NAME}"
echo "   Scope: ${RESOURCE_GROUP}"
echo "=========================================================="

SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
TENANT_ID="$(az account show --query tenantId -o tsv)"

# --- 1. Registro de aplicación -----------------------------------------------
echo "[1/4] Registro de aplicación en Entra ID..."
APP_ID="$(az ad app list --display-name "${APP_NAME}" --query "[0].appId" -o tsv 2>/dev/null || true)"
if [[ -z "${APP_ID}" || "${APP_ID}" == "null" ]]; then
  if ! APP_ID="$(az ad app create --display-name "${APP_NAME}" --query appId -o tsv 2>/dev/null)"; then
    echo "    [ERROR] No se pudo registrar la aplicación."
    echo "            Suele ser falta de permisos en Entra ID: en suscripciones de"
    echo "            estudiante el registro de aplicaciones puede estar restringido."
    echo "            Pide a un administrador del tenant que lo cree, o mantén el"
    echo "            despliegue manual con 'az login' desde tu máquina."
    exit 1
  fi
  echo "    aplicación creada: ${APP_ID}"
else
  echo "    ya existe: ${APP_ID}"
fi

# --- 2. Service principal -----------------------------------------------------
echo "[2/4] Service principal..."
if ! az ad sp show --id "${APP_ID}" &>/dev/null; then
  az ad sp create --id "${APP_ID}" --output none
fi
SP_OID="$(az ad sp show --id "${APP_ID}" --query id -o tsv)"

# --- 3. Credenciales federadas ------------------------------------------------
# El `subject` es lo que ata el token a un origen concreto. Sin esto, cualquier
# repositorio de GitHub podría pedir un token para esta aplicación.
echo "[3/4] Credenciales federadas..."
crear_federacion() {  # nombre, subject, descripción
  local nombre="$1" subject="$2" descripcion="$3"
  if az ad app federated-credential show --id "${APP_ID}" --federated-credential-id "${nombre}" &>/dev/null; then
    echo "    '${nombre}' ya existe."
    return 0
  fi
  az ad app federated-credential create --id "${APP_ID}" --parameters "{
    \"name\": \"${nombre}\",
    \"issuer\": \"https://token.actions.githubusercontent.com\",
    \"subject\": \"${subject}\",
    \"description\": \"${descripcion}\",
    \"audiences\": [\"api://AzureADTokenExchange\"]
  }" --output none 2>/dev/null \
    && echo "    '${nombre}' creada." \
    || echo "    [AVISO] no se pudo crear '${nombre}'."
}

for ENVIRONMENT_NAME in "${ENVIRONMENTS[@]}"; do
  crear_federacion "gh-env-${ENVIRONMENT_NAME}" \
    "repo:${GITHUB_REPO}:environment:${ENVIRONMENT_NAME}" \
    "Despliegue desde el entorno ${ENVIRONMENT_NAME}"
done
for BRANCH in "${BRANCHES[@]}"; do
  crear_federacion "gh-branch-${BRANCH}" \
    "repo:${GITHUB_REPO}:ref:refs/heads/${BRANCH}" \
    "Despliegue desde la rama ${BRANCH}"
done

# --- 4. RBAC de menor privilegio ---------------------------------------------
# Contributor ACOTADO al grupo de recursos, no a la suscripción: el pipeline
# puede desplegar Centinela y nada más. Sin 'Owner' ni 'User Access
# Administrator', así que tampoco puede repartirse permisos a sí mismo.
echo "[4/4] Asignando RBAC sobre ${RESOURCE_GROUP}..."
RG_ID="$(az group show -n "${RESOURCE_GROUP}" --query id -o tsv)"
az role assignment create --assignee-object-id "${SP_OID}" \
  --assignee-principal-type ServicePrincipal \
  --role "Contributor" --scope "${RG_ID}" --output none 2>/dev/null \
  && echo "    Contributor asignado." || echo "    ya estaba asignado."

# --- Resumen ------------------------------------------------------------------
cat <<RESUMEN

==========================================================
 Listo. Configura estas VARIABLES en GitHub
==========================================================
  Settings → Secrets and variables → Actions → Variables → New variable

    AZURE_CLIENT_ID        ${APP_ID}
    AZURE_TENANT_ID        ${TENANT_ID}
    AZURE_SUBSCRIPTION_ID  ${SUBSCRIPTION_ID}
    AZURE_SUFFIX           ${SUFFIX}

 Son identificadores PÚBLICOS, no credenciales: van como *variables*, no como
 secrets. Sin la federación de arriba no sirven para autenticarse.

 Después, en Settings → Environments, crea 'dev' y 'prod'. En 'prod' activa
 "Required reviewers" para que el despliegue a producción pase por aprobación.

 Y borra el secreto que ya no hace falta:
    Settings → Secrets → Actions → AZURE_CREDENTIALS → Remove
 Es un service principal con clientSecret de larga duración; con OIDC en
 marcha, mantenerlo solo deja superficie de ataque abierta.
==========================================================
RESUMEN
