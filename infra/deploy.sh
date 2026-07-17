#!/usr/bin/env bash
# Despliegue de infraestructura CENTINELA.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=variables.sh
source "${SCRIPT_DIR}/variables.sh"

echo "Desplegando ${PROJECT_NAME} (${ENVIRONMENT}) en ${LOCATION}..."
echo "Resource group: ${RESOURCE_GROUP}"

# TODO: añadir comandos de despliegue (az, bicep, terraform, etc.)
echo "Deploy pendiente de implementación."
