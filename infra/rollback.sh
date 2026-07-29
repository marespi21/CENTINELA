#!/usr/bin/env bash
# =============================================================================
# CENTINELA — Vuelta atrás de un despliegue en Container Apps (Sprint 6, Fase 5)
# =============================================================================
# Devuelve la API y el worker a la imagen que corrían ANTES del último
# despliegue, leyendo el historial de revisiones de Container Apps.
#
# Por qué se hace por imagen y no repartiendo tráfico: las apps están en modo de
# revisión ÚNICA (el de por defecto), donde solo hay una revisión activa a la
# vez y `ingress traffic set` no aplica. Volver atrás es, literalmente, volver a
# desplegar la imagen anterior — que además funciona igual para el worker, que
# no tiene ingress ni tráfico que repartir.
#
# Uso:
#   bash infra/rollback.sh                 # a la revisión inmediatamente anterior
#   bash infra/rollback.sh sha-abc1234     # a una etiqueta concreta
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=variables.sh
source "${SCRIPT_DIR}/variables.sh"

TARGET_TAG="${1:-}"

echo "=========================================================="
echo " Rollback — ${RESOURCE_GROUP}"
echo "=========================================================="

imagen_anterior() {  # nombre de la container app
  local app="$1"
  # Revisiones ordenadas de más nueva a más vieja; se toma la SEGUNDA, que es
  # la que estaba sirviendo antes del despliegue actual.
  az containerapp revision list -g "${RESOURCE_GROUP}" -n "${app}" \
    --query "sort_by([].{created:properties.createdTime, image:properties.template.containers[0].image}, &created) | reverse(@) | [1].image" \
    -o tsv 2>/dev/null || true
}

revertir() {  # nombre de la container app, imagen base del registro
  local app="$1" imagen_base="$2"
  local destino=""

  if [[ -n "${TARGET_TAG}" ]]; then
    destino="${imagen_base}:${TARGET_TAG}"
  else
    destino="$(imagen_anterior "${app}")"
  fi

  if [[ -z "${destino}" || "${destino}" == "None" ]]; then
    echo "  [ERROR] ${app}: no hay revisión anterior a la que volver."
    echo "          Indica una etiqueta explícita:  bash infra/rollback.sh sha-abc1234"
    return 1
  fi

  local actual
  actual="$(az containerapp show -g "${RESOURCE_GROUP}" -n "${app}" \
    --query "properties.template.containers[0].image" -o tsv 2>/dev/null || true)"

  if [[ "${actual}" == "${destino}" ]]; then
    echo "  ${app}: ya está en ${destino}; nada que hacer."
    return 0
  fi

  echo "  ${app}"
  echo "    actual:  ${actual}"
  echo "    destino: ${destino}"
  az containerapp update -g "${RESOURCE_GROUP}" -n "${app}" \
    --image "${destino}" --output none
  echo "    revertido."
}

FALLOS=0
revertir "${ACA_API}"    "${IMAGE_API}"    || FALLOS=$((FALLOS + 1))
revertir "${ACA_WORKER}" "${IMAGE_WORKER}" || FALLOS=$((FALLOS + 1))

if [[ ${FALLOS} -gt 0 ]]; then
  echo
  echo "RESULTADO: ${FALLOS} aplicación(es) sin revertir."
  exit 1
fi

# Verificar que la API responde tras volver atrás: un rollback que deja el
# servicio caído no es un rollback.
API_FQDN="$(az containerapp show -g "${RESOURCE_GROUP}" -n "${ACA_API}" \
  --query properties.configuration.ingress.fqdn -o tsv 2>/dev/null || true)"
if [[ -n "${API_FQDN}" ]]; then
  echo
  echo "Comprobando la salud de la API tras el rollback..."
  for INTENTO in $(seq 1 10); do
    CODIGO="$(curl -s -o /dev/null -w '%{http_code}' "https://${API_FQDN}/health" || true)"
    if [[ "${CODIGO}" == "200" ]]; then
      echo "  API sana (HTTP 200) tras ${INTENTO} intento(s)."
      break
    fi
    [[ ${INTENTO} -eq 10 ]] && {
      echo "  [AVISO] la API no respondió 200 tras el rollback (último: ${CODIGO})."
      exit 1
    }
    sleep 6
  done
fi

echo
echo "Rollback completado."
