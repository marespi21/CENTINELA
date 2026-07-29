#!/usr/bin/env bash
# =============================================================================
# CENTINELA — Alertas y consultas de observabilidad (Sprint 6, Fase 3)
# =============================================================================
# La instrumentación ya emite trazas, métricas y logs correlacionados. Esto
# monta encima lo que convierte esos datos en operabilidad: alertas que avisan
# solas y consultas guardadas para investigar.
#
# Se apoya en el workspace de Log Analytics y el Application Insights que creó
# infra/containerapps.sh. No crea cómputo nuevo: coste 0 más allá de la ingesta,
# que va contra los 5 GB/mes gratuitos.
#
# Uso:  export SUFFIX=sp5x1 && bash infra/observability.sh
#       export ALERT_EMAIL=tu@correo   # para recibir los avisos
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=variables.sh
source "${SCRIPT_DIR}/variables.sh"

APP_INSIGHTS="appi-${PROJECT}-${ENV}${SUFFIX:+-${SUFFIX}}"
ACTION_GROUP="ag-${PROJECT}-${ENV}${SUFFIX:+-${SUFFIX}}"
ALERT_EMAIL="${ALERT_EMAIL:-${BUDGET_ALERT_EMAIL}}"

echo "=========================================================="
echo " Observabilidad — ${APP_INSIGHTS}"
echo "=========================================================="

WORKSPACE_ID="$(az monitor log-analytics workspace show \
  -g "${RESOURCE_GROUP}" -n "${LOG_WORKSPACE}" --query id -o tsv 2>/dev/null || true)"
if [[ -z "${WORKSPACE_ID}" ]]; then
  echo "[ERROR] No existe el workspace ${LOG_WORKSPACE}."
  echo "        Ejecuta antes: bash infra/containerapps.sh"
  exit 1
fi

# --- 1. Grupo de acción (a dónde van los avisos) -----------------------------
echo "[1/3] Grupo de acción ${ACTION_GROUP} (destino: ${ALERT_EMAIL})..."
az monitor action-group create \
  -g "${RESOURCE_GROUP}" -n "${ACTION_GROUP}" --short-name centinela \
  --action email admin "${ALERT_EMAIL}" \
  --output none 2>/dev/null || echo "    ya existe; se reutiliza."

ACTION_GROUP_ID="$(az monitor action-group show -g "${RESOURCE_GROUP}" -n "${ACTION_GROUP}" \
  --query id -o tsv 2>/dev/null || true)"

# --- 2. Alertas ---------------------------------------------------------------
# Cada una responde a un fallo REAL observado o previsto en este sistema, no a
# una métrica genérica de manual.
echo "[2/3] Alertas..."

crear_alerta() {  # nombre, descripción, consulta KQL, frecuencia(min), ventana(min), umbral
  local nombre="$1" descripcion="$2" consulta="$3" frecuencia="$4" ventana="$5" umbral="$6"
  if az monitor scheduled-query show -g "${RESOURCE_GROUP}" -n "${nombre}" &>/dev/null; then
    echo "    '${nombre}' ya existe."
    return 0
  fi
  az monitor scheduled-query create \
    -g "${RESOURCE_GROUP}" -n "${nombre}" \
    --scopes "${WORKSPACE_ID}" \
    --description "${descripcion}" \
    --condition "count 'consulta' > ${umbral}" \
    --condition-query consulta="${consulta}" \
    --evaluation-frequency "${frecuencia}m" \
    --window-size "${ventana}m" \
    --severity 2 \
    ${ACTION_GROUP_ID:+--action-groups "${ACTION_GROUP_ID}"} \
    --output none 2>/dev/null \
    && echo "    '${nombre}' creada." \
    || echo "    [AVISO] no se pudo crear '${nombre}'."
}

# Mensajes envenenados: significa que hay transacciones o casos que el sistema
# NO consiguió procesar tras varios intentos. Es pérdida funcional silenciosa.
crear_alerta "alerta-mensajes-envenenados" \
  "Mensajes apartados a la cola poison: hay casos que no se procesaron" \
  'ContainerAppConsoleLogs_CL | where Log_s has "mensaje envenenado apartado"' \
  5 15 0

# El worker deja de puntuar mientras siguen entrando transacciones: la cola
# crece y los casos de fraude no llegan a la bandeja del analista.
crear_alerta "alerta-worker-con-errores" \
  "El worker acumula errores procesando la cola" \
  'ContainerAppConsoleLogs_CL | where Log_s has "error sondeando la cola"' \
  5 15 3

# El OCR agotó la cuota gratuita F0 (500 páginas/mes) o está caído.
crear_alerta "alerta-ocr-fallando" \
  "Document Intelligence rechaza documentos (posible cuota F0 agotada)" \
  'ContainerAppConsoleLogs_CL | where Log_s has "Document Intelligence no pudo procesar"' \
  15 60 2

# --- 3. Consultas guardadas ---------------------------------------------------
echo "[3/3] Consultas guardadas para investigar..."
guardar_consulta() {  # nombre, categoría, KQL
  az monitor log-analytics workspace saved-search create \
    -g "${RESOURCE_GROUP}" --workspace-name "${LOG_WORKSPACE}" \
    --saved-search-id "$1" --display-name "$1" --category "$2" --saved-query "$3" \
    --output none 2>/dev/null && echo "    '$1' guardada." || echo "    [AVISO] '$1' no se pudo guardar."
}

# Seguir un caso concreto de punta a punta. Es lo que la Fase 3 hace posible:
# antes, el trace_id no cruzaba las colas y esta consulta no devolvía la cadena
# completa, solo trozos sueltos.
guardar_consulta "centinela-traza-completa" "Centinela" \
  'ContainerAppConsoleLogs_CL
| extend trace = extract("trace=([a-f0-9]{32})", 1, Log_s)
| where isnotempty(trace)
| where trace == "PEGA_AQUI_EL_TRACE_ID"
| project TimeGenerated, ContainerAppName_s, Log_s
| order by TimeGenerated asc'

guardar_consulta "centinela-latencia-extremo-a-extremo" "Centinela" \
  'ContainerAppConsoleLogs_CL
| where Log_s has "persisted case="
| summarize casos = count() by bin(TimeGenerated, 5m)
| render timechart'

guardar_consulta "centinela-veredictos-documentales" "Centinela" \
  'ContainerAppConsoleLogs_CL
| where Log_s has "documento verificado"
| extend veredicto = extract("veredicto=([a-z]+)", 1, Log_s)
| summarize total = count() by veredicto
| render piechart'

guardar_consulta "centinela-reglas-mas-activadas" "Centinela" \
  'ContainerAppConsoleLogs_CL
| where Log_s has "scored transaction="
| extend reglas = extract(@"rules=\[(.*?)\]", 1, Log_s)
| where isnotempty(reglas)
| summarize veces = count() by reglas
| order by veces desc'

echo
echo "=========================================================="
echo " Observabilidad configurada"
echo "=========================================================="
echo "  Application Insights: ${APP_INSIGHTS}"
echo "  Alertas → ${ALERT_EMAIL}"
echo
echo "  Trazas de punta a punta (API → cola → worker → PostgreSQL):"
echo "    portal.azure.com → ${APP_INSIGHTS} → Transaction search"
echo
echo "  Métricas de negocio publicadas por el worker:"
echo "    centinela.transacciones.evaluadas, centinela.casos.abiertos,"
echo "    centinela.scoring.duracion, centinela.reglas.activadas,"
echo "    centinela.documentos.verificados,"
echo "    centinela.caso.latencia_extremo_a_extremo"
