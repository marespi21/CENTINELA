#!/usr/bin/env bash
# Verificación de secretos (módulo Lukas, Semana 4).
# Comprueba que:
#   1. Los secretos vivan en Key Vault.
#   2. Los app settings los consuman POR REFERENCIA (@Microsoft.KeyVault), no en claro.
#   3. No haya secretos hardcodeados en el repositorio.
#
# Uso: bash infra/verify_secrets.sh   (requiere az login para 1 y 2).

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=variables.sh
source "${SCRIPT_DIR}/variables.sh"

FAIL=0

echo "== 1. Secretos presentes en Key Vault (${KEY_VAULT}) =="
for name in api-keys cosmos-db-key cases-db-dsn db-admin-password; do
  if az keyvault secret show --vault-name "${KEY_VAULT}" --name "${name}" &>/dev/null; then
    echo "  [OK]    '${name}' presente"
  else
    echo "  [FALTA] '${name}' NO está en el vault"
    FAIL=1
  fi
done

echo "== 2. App settings consumidos por referencia (no en claro) =="
for setting in COSMOS_KEY CASES_DB_DSN; do
  VAL="$(az webapp config appsettings list \
    --resource-group "${RESOURCE_GROUP}" --name "${WEBAPP}" \
    --query "[?name=='${setting}'].value | [0]" -o tsv 2>/dev/null || true)"
  if [[ -z "${VAL}" ]]; then
    echo "  [FALTA]  '${setting}' no configurado en ${WEBAPP}"
    FAIL=1
  elif echo "${VAL}" | grep -q "@Microsoft.KeyVault"; then
    echo "  [OK]     '${setting}' por referencia a Key Vault"
  else
    echo "  [ALERTA] '${setting}' parece estar EN CLARO (no es referencia)"
    FAIL=1
  fi
done

echo "== 3. Sin secretos hardcodeados en el repositorio =="
HITS="$(git -C "${SCRIPT_DIR}/.." grep -nE \
  "AccountKey=[A-Za-z0-9/+]{20,}|AccountEndpoint=.*AccountKey|-----BEGIN (RSA |OPENSSH )?PRIVATE KEY" \
  -- . 2>/dev/null | grep -viE "example|placeholder|devstoreaccount1|<|getenv" || true)"
if [[ -n "${HITS}" ]]; then
  echo "  [ALERTA] posibles secretos hardcodeados:"
  echo "${HITS}"
  FAIL=1
else
  echo "  [OK] sin secretos hardcodeados evidentes"
fi

echo
if [[ "${FAIL}" -eq 0 ]]; then
  echo "== VERIFICACIÓN OK: secretos en Key Vault y consumidos por referencia =="
else
  echo "== HAY FALLOS: revisar los puntos marcados arriba =="
  exit 1
fi
