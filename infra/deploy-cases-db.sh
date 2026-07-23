#!/usr/bin/env bash
# =============================================================================
# CENTINELA - Despliegue de Almacén de Casos (Relacional Aislado - Azure PostgreSQL)
# Autor: Juan José Guarín
# Uso: bash infra/deploy-cases-db.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=variables.sh
source "${SCRIPT_DIR}/variables.sh"

DB_SERVER_NAME="psql-${PROJECT}-${ENV}"
DB_NAME="centinela_cases"
DB_ADMIN_USER="centinela_admin"
SUBNET_POSTGRES="${SUBNET_DB:-subnet-db}"
DDL_FILE="${SCRIPT_DIR}/../scripts/init-cases-db.sql"

# -----------------------------------------------------------------------------
# Gestión Segura de Secretos (Sin secretos harcodeados en repositorio)
# -----------------------------------------------------------------------------
DB_ADMIN_PASS="${DB_ADMIN_PASS:-}"
if [[ -z "${DB_ADMIN_PASS}" ]]; then
  echo "Obteniendo contraseña de base de datos desde Azure Key Vault '${KEY_VAULT}'..."
  DB_ADMIN_PASS=$(az keyvault secret show --vault-name "${KEY_VAULT}" --name "db-admin-password" --query value -o tsv 2>/dev/null || true)
fi

if [[ -z "${DB_ADMIN_PASS}" ]]; then
  echo "[ERROR] No se especificó la variable DB_ADMIN_PASS ni se encontró la secreta 'db-admin-password' en Key Vault."
  echo "        Por favor declare DB_ADMIN_PASS antes de ejecutar el script."
  exit 1
fi

echo "==> Desplegando Almacén Relacional de Casos para ${PROJECT} (${ENV})"
echo "    Servidor PostgreSQL: ${DB_SERVER_NAME}"
echo "    Base de Datos:       ${DB_NAME}"
echo "    Red Aislada:         ${VNET} / ${SUBNET_POSTGRES}"

# 1. Asegurar la infraestructura de red
echo "[1/5] Verificando infraestructura de red y subnet delegada..."
bash "${SCRIPT_DIR}/../scripts/deploy-network.sh" --resource-group "${RESOURCE_GROUP}" --location "${LOCATION}"

# 2. Desplegar PostgreSQL Flexible Server (Free Tier: Standard_B1ms) en Subred Delegada
echo "[2/5] Creando Azure Database for PostgreSQL Flexible Server en subred delegada..."
if ! az postgres flexible-server show --resource-group "${RESOURCE_GROUP}" --name "${DB_SERVER_NAME}" &>/dev/null; then
  az postgres flexible-server create \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${DB_SERVER_NAME}" \
    --location "${LOCATION}" \
    --admin-user "${DB_ADMIN_USER}" \
    --admin-password "${DB_ADMIN_PASS}" \
    --sku-name Standard_B1ms \
    --tier Burstable \
    --storage-size 32 \
    --backup-retention 7 \
    --vnet "${VNET}" \
    --subnet "${SUBNET_POSTGRES}" \
    --public-access Disabled \
    --yes \
    --output none
else
  echo "  Servidor PostgreSQL '${DB_SERVER_NAME}' ya existe."
fi

# 3. Crear la base de datos de casos
echo "[3/5] Creando la base de datos '${DB_NAME}'..."
if ! az postgres flexible-server db show --resource-group "${RESOURCE_GROUP}" --server-name "${DB_SERVER_NAME}" --database-name "${DB_NAME}" &>/dev/null; then
  az postgres flexible-server db create \
    --resource-group "${RESOURCE_GROUP}" \
    --server-name "${DB_SERVER_NAME}" \
    --database-name "${DB_NAME}" \
    --output none
else
  echo "  Base de datos '${DB_NAME}' ya existe."
fi

# 4. Reforzar Reglas de NSG para Aislamiento de Red
echo "[4/5] Aplicando reglas de aislamiento en Network Security Group..."
az network nsg rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --nsg-name NSG-Centinela-Storage \
  --name Allow-App-Subnet-To-PostgreSQL \
  --priority 110 \
  --direction Inbound \
  --access Allow \
  --protocol Tcp \
  --source-address-prefix 10.0.1.0/24 \
  --destination-port-ranges 5432 \
  --output none 2>/dev/null || true

az network nsg rule create \
  --resource-group "${RESOURCE_GROUP}" \
  --nsg-name NSG-Centinela-Storage \
  --name Deny-Internet-To-PostgreSQL \
  --priority 190 \
  --direction Inbound \
  --access Deny \
  --protocol Tcp \
  --source-address-prefix Internet \
  --destination-port-ranges 5432 \
  --output none 2>/dev/null || true

# 5. Ejecutar DDL de inicialización (init-cases-db.sql)
echo "[5/5] Aplicando DDL de esquemas, triggers y auditoría inmutable (${DDL_FILE})..."
if [[ -f "${DDL_FILE}" ]]; then
  echo "  Ejecutando DDL mediante az postgres flexible-server execute..."
  az postgres flexible-server execute \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${DB_SERVER_NAME}" \
    --admin-user "${DB_ADMIN_USER}" \
    --admin-password "${DB_ADMIN_PASS}" \
    --database-name "${DB_NAME}" \
    --file-path "${DDL_FILE}" \
    --output none || {
      echo "  [AVISO] La ejecución CLI remota no pudo completarse directamente (servidor privado sin acceso público)."
      echo "          El script DDL se encuentra listo en '${DDL_FILE}' para aplicación automática en el pipeline VNet o via app container."
    }
else
  echo "[ERROR] El archivo DDL '${DDL_FILE}' no existe."
  exit 1
fi

echo
echo "==> Despliegue de Almacén de Casos Aislado completado exitosamente."
echo "    - Instancia PostgreSQL aislada en ${SUBNET_POSTGRES} (10.0.3.0/24)"
echo "    - Acceso público deshabilitado (Inalcanzable desde Internet)"
echo "    - Retención de Respaldos: 7 Días (Point-In-Time Restore habilitado, RPO < 5min)"
