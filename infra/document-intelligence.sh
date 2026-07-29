#!/usr/bin/env bash
# =============================================================================
# CENTINELA — Azure AI Document Intelligence (Sprint 6, Fase 2)
# =============================================================================
# Aprovisiona el servicio de OCR que verifica los comprobantes adjuntos a un
# caso, en su capa **gratuita F0** (500 páginas/mes).
#
# Autenticación por Managed Identity, SIN clave: para que el servicio acepte
# tokens de Entra ID hace falta que tenga un *subdominio personalizado*, así que
# se crea con `--custom-domain`. A la identidad del worker se le concede el rol
# "Cognitive Services User", que solo permite invocar el análisis.
#
# Es idempotente y NO destruye nada: si el recurso ya existe, se reutiliza.
#
# Uso:  export SUFFIX=sp5x1 && bash infra/document-intelligence.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=variables.sh
source "${SCRIPT_DIR}/variables.sh"

echo "=========================================================="
echo " Document Intelligence — ${DOC_INTELLIGENCE} (${DOC_INTELLIGENCE_SKU})"
echo "=========================================================="

echo "[1/3] Registrando el provider de Cognitive Services..."
az provider register --namespace Microsoft.CognitiveServices --wait --output none 2>/dev/null || true

echo "[2/3] Creando el recurso (capa ${DOC_INTELLIGENCE_SKU})..."
if az cognitiveservices account show -g "${RESOURCE_GROUP}" -n "${DOC_INTELLIGENCE}" &>/dev/null; then
  echo "    ya existe; se reutiliza."
else
  # --kind FormRecognizer es el identificador de Document Intelligence en la
  # CLI (conserva el nombre anterior del servicio).
  if ! az cognitiveservices account create \
      --resource-group "${RESOURCE_GROUP}" --name "${DOC_INTELLIGENCE}" \
      --kind FormRecognizer --sku "${DOC_INTELLIGENCE_SKU}" \
      --location "${DOC_INTELLIGENCE_LOCATION}" \
      --custom-domain "${DOC_INTELLIGENCE}" \
      --yes --output none 2>/dev/null; then
    echo "    [ERROR] No se pudo crear el recurso. Causas habituales:"
    echo "      - Ya existe otra instancia F0 de FormRecognizer en la suscripción"
    echo "        (Azure solo permite una). Reutilízala poniendo DOC_INTELLIGENCE"
    echo "        al nombre de la existente."
    echo "      - La región ${DOC_INTELLIGENCE_LOCATION} no ofrece el servicio."
    echo "      - Falta aceptar los Términos de IA Responsable en el portal."
    exit 1
  fi
fi

DI_ENDPOINT="$(az cognitiveservices account show -g "${RESOURCE_GROUP}" -n "${DOC_INTELLIGENCE}" \
  --query properties.endpoint -o tsv)"

echo "[3/3] Concediendo acceso a la identidad del worker (sin claves)..."
IDENTITY_PRINCIPAL="$(az identity show -g "${RESOURCE_GROUP}" -n "${ACA_IDENTITY}" \
  --query principalId -o tsv 2>/dev/null || true)"
DI_ID="$(az cognitiveservices account show -g "${RESOURCE_GROUP}" -n "${DOC_INTELLIGENCE}" \
  --query id -o tsv)"

if [[ -n "${IDENTITY_PRINCIPAL}" ]]; then
  # "Cognitive Services User" permite INVOCAR el análisis, no administrar el
  # recurso ni leer sus claves: menor privilegio.
  az role assignment create --assignee-object-id "${IDENTITY_PRINCIPAL}" \
    --assignee-principal-type ServicePrincipal \
    --role "Cognitive Services User" --scope "${DI_ID}" --output none 2>/dev/null || true
  echo "    rol asignado a ${ACA_IDENTITY}."
else
  echo "    [AVISO] La identidad ${ACA_IDENTITY} aún no existe."
  echo "            Ejecuta antes infra/containerapps.sh y vuelve a lanzar este script."
fi

echo
echo "=========================================================="
echo " Listo."
echo "   DOC_INTELLIGENCE_ENDPOINT=${DI_ENDPOINT}"
echo "   Modelo: ${DOC_INTELLIGENCE_MODEL}   Capa: ${DOC_INTELLIGENCE_SKU} (gratuita)"
echo
echo " No se ha guardado ninguna clave: el worker se autentica con su Managed"
echo " Identity. Aplica el endpoint al worker con:"
echo "   bash infra/containerapps.sh"
echo "=========================================================="
