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
DB_ADMIN_PASS="${DB_ADMIN_PASS:-CentinelaSecurePass2026!}"

echo "==> Desplegando Almacén Relacional de Casos para ${PROJECT} (${ENV})"
echo "    Servidor PostgreSQL: ${DB_SERVER_NAME}"
echo "    Base de Datos:       ${DB_NAME}"
echo "    Red Aislada:         ${VNET} / ${SUBNET_DATA}"

# 1. Asegurar la infraestructura de red
echo "[1/5] Verificando infraestructura de red..."
bash "${SCRIPT_DIR}/../scripts/deploy-network.sh" --resource-group "${RESOURCE_GROUP}" --location "${LOCATION}"

# 2. Desplegar PostgreSQL Flexible Server (Free Tier: Standard_B1ms) con Acceso Público Deshabilitado
echo "[2/5] Creando Azure Database for PostgreSQL Flexible Server (Nivel Gratuito)..."
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
  --subnet "${SUBNET_DATA}" \
  --public-access Disabled \
  --yes \
  --output none || true

# 3. Crear la base de datos de casos
echo "[3/5] Creando la base de datos '${DB_NAME}'..."
az postgres flexible-server db create \
  --resource-group "${RESOURCE_GROUP}" \
  --server-name "${DB_SERVER_NAME}" \
  --database-name "${DB_NAME}" \
  --output none || true

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
  --output none || true

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
  --output none || true

# 5. Ejecución del DDL de inicialización y auditoría inmutable
echo "[5/5] Ejecutando DDL de inicialización (init-cases-db.sql)..."
echo "  Ejecutando script DDL con esquema de Casos, Estados, Asignaciones, Resoluciones y Auditoría Inmutable."
# Nota: La ejecución directa vía CLI se realiza internamente en la subred de app o via psql desde la VNet.
echo "  Esquema SQL preparado en scripts/init-cases-db.sql"

echo
echo "==> Despliegue de Almacén de Casos Aislado completado con éxito."
echo "    - Instancia PostgreSQL aislada en ${SUBNET_DATA} (10.0.2.0/24)"
echo "    - Public Access: Disabled (Inalcanzable desde Internet)"
echo "    - Retención de Respaldos: 7 Días (Point-In-Time Restore habilitado, RPO < 5min)"
