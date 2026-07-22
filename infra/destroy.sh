#!/usr/bin/env bash
# Destrucción de infraestructura CENTINELA.
# Uso: bash infra/destroy.sh
# Elimina el Resource Group completo (y todos sus recursos).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=variables.sh
source "${SCRIPT_DIR}/variables.sh"

echo "==> Destruyendo recursos de ${PROJECT} (${ENV})"
echo "    Resource group: ${RESOURCE_GROUP}"
echo
echo "ADVERTENCIA: esto elimina TODOS los recursos del grupo."
read -r -p "Escribe el nombre del resource group para confirmar: " CONFIRM

if [[ "${CONFIRM}" != "${RESOURCE_GROUP}" ]]; then
  echo "Confirmación incorrecta. Abortado."
  exit 1
fi

az group delete \
  --name "${RESOURCE_GROUP}" \
  --yes \
  --no-wait

rm -f "${SCRIPT_DIR}/principal_id.txt"

echo
echo "==> Eliminación iniciada (async). Verificar con:"
echo "  az group show --name ${RESOURCE_GROUP}"
