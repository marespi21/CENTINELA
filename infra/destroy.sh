#!/usr/bin/env bash
# Destrucción de infraestructura CENTINELA.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=variables.sh
source "${SCRIPT_DIR}/variables.sh"

echo "Destruyendo recursos de ${PROJECT_NAME} (${ENVIRONMENT})..."
echo "Resource group: ${RESOURCE_GROUP}"

# TODO: añadir comandos de destrucción
echo "Destroy pendiente de implementación."
