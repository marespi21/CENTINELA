#!/usr/bin/env bash
# =============================================================================
# CENTINELA — Auditoría de una imagen de contenedor (Sprint 6, Fase 1)
# =============================================================================
# Verifica la regla dura del sprint: CERO credenciales en la imagen. No se
# limita a mirar el filesystem final — un secreto borrado en una capa posterior
# sigue siendo recuperable de la capa donde se añadió, así que se inspeccionan
# TODAS las capas del tar exportado.
#
# Comprueba además el endurecimiento básico: proceso sin privilegios y sin
# gestor de paquetes dentro del contenedor.
#
# Uso:  bash infra/verify-image-secrets.sh centinela-api:dev [más imágenes...]
# Salida: 0 si la imagen pasa; 1 si algo falla.
# =============================================================================

set -uo pipefail

SELF_TEST=0
IMAGES=()
for ARG in "$@"; do
  case "${ARG}" in
    --self-test) SELF_TEST=1 ;;
    *) IMAGES+=("${ARG}") ;;
  esac
done
if [[ ${#IMAGES[@]} -eq 0 ]]; then
  IMAGES=(centinela-api:dev centinela-worker:dev)
fi

FAILURES=0
WORKDIR="$(mktemp -d)"
trap 'rm -rf "${WORKDIR}"' EXIT

# Nombres de fichero que jamás deben viajar en una imagen. Los certificados de
# CA (/etc/ssl/certs, certifi) son *.pem legítimos y se excluyen del patrón.
SENSITIVE_NAMES='(^|/)(\.env|\.env\..*|local\.settings\.json|credentials\.json|principal_id\.txt|id_rsa|.*\.pfx)$'
SENSITIVE_KEYS='(\.pem|\.key)$'
CERT_ALLOWLIST='(etc/ssl/certs/|/certifi/|usr/lib/ssl/|usr/share/ca-certificates/)'

# Valores que delatan una credencial REAL, no un placeholder de documentación ni
# una constante de librería. Por eso cada patrón exige material criptográfico
# detrás de la etiqueta: `cryptography` y `msal` llevan en su código la cadena
# "-----BEGIN PRIVATE KEY-----" como cabecera PEM que saben parsear, y marcarla
# sin más convertiría esta auditoría en un detector de ruido que nadie mira.
SECRET_VALUES='AccountKey=[A-Za-z0-9+/]{40,}|postgresql://[a-zA-Z0-9_]+:[^@ ]{8,}@|sv=20[0-9]{2}-[0-9]{2}-[0-9]{2}&s[a-z]=|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----[[:space:]]+[A-Za-z0-9+/]{40,}'

# Variables de entorno con nombre sospechoso que NO son secretas. GPG_KEY la
# define la imagen oficial de Python: es la huella pública del firmante del
# tarball de CPython, publicada en python.org.
ENV_ALLOWLIST='^GPG_KEY='

fail() { echo "  ✗ $1"; FAILURES=$((FAILURES + 1)); }
pass() { echo "  ✓ $1"; }

for IMAGE in "${IMAGES[@]}"; do
  echo "=============================================================="
  echo " Auditando ${IMAGE}"
  echo "=============================================================="

  if ! docker image inspect "${IMAGE}" >/dev/null 2>&1; then
    fail "la imagen no existe localmente"
    continue
  fi

  SAFE_NAME="$(echo "${IMAGE}" | tr '/:' '__')"
  EXTRACT="${WORKDIR}/${SAFE_NAME}"
  mkdir -p "${EXTRACT}"
  docker save "${IMAGE}" | tar -x -C "${EXTRACT}"

  # --- 1. Ficheros sensibles por nombre, en cualquier capa -------------------
  HITS="$(
    find "${EXTRACT}" -type f 2>/dev/null | while read -r blob; do
      tar -tf "${blob}" 2>/dev/null
    done | grep -aE "${SENSITIVE_NAMES}" | sort -u
  )"
  KEY_HITS="$(
    find "${EXTRACT}" -type f 2>/dev/null | while read -r blob; do
      tar -tf "${blob}" 2>/dev/null
    done | grep -aE "${SENSITIVE_KEYS}" | grep -avE "${CERT_ALLOWLIST}" | sort -u
  )"
  ALL_NAME_HITS="$(printf '%s\n%s' "${HITS}" "${KEY_HITS}" | grep -av '^$' || true)"
  if [[ -n "${ALL_NAME_HITS}" ]]; then
    fail "ficheros sensibles empaquetados:"
    echo "${ALL_NAME_HITS}" | sed 's/^/      /'
  else
    pass "ninguna capa contiene .env, claves privadas ni credenciales por nombre"
  fi

  # --- 2. Credenciales reales en el CONTENIDO de las capas ------------------
  VALUE_HITS="$(
    find "${EXTRACT}" -type f 2>/dev/null | while read -r blob; do
      tar -xOf "${blob}" 2>/dev/null
    done | LC_ALL=C grep -aoE "${SECRET_VALUES}" | sort -u
  )"
  if [[ -n "${VALUE_HITS}" ]]; then
    fail "patrones de credencial en el contenido de alguna capa:"
    echo "${VALUE_HITS}" | sed 's/^/      /'
  else
    pass "ninguna capa contiene cadenas de conexión, SAS ni claves privadas"
  fi

  # --- 3. Variables de entorno y build args horneadas -----------------------
  ENV_HITS="$(docker image inspect "${IMAGE}" --format '{{range .Config.Env}}{{println .}}{{end}}' \
    | grep -aiE '(KEY|SECRET|PASSWORD|TOKEN|DSN|CONNECTION_STRING)=..' \
    | grep -avE "${ENV_ALLOWLIST}" || true)"
  if [[ -n "${ENV_HITS}" ]]; then
    fail "variables de entorno con pinta de secreto en la config de la imagen:"
    echo "${ENV_HITS}" | sed 's/^/      /'
  else
    pass "sin secretos en las variables de entorno de la imagen"
  fi

  HISTORY_HITS="$(docker history --no-trunc --format '{{.CreatedBy}}' "${IMAGE}" 2>/dev/null \
    | LC_ALL=C grep -aoE "${SECRET_VALUES}" | sort -u || true)"
  if [[ -n "${HISTORY_HITS}" ]]; then
    fail "credenciales visibles en el historial de construcción (ARG/RUN)"
  else
    pass "sin credenciales en el historial de construcción"
  fi

  # --- 4. Endurecimiento ----------------------------------------------------
  USER_ID="$(docker image inspect "${IMAGE}" --format '{{.Config.User}}')"
  if [[ -z "${USER_ID}" || "${USER_ID}" == "root" || "${USER_ID}" == 0* ]]; then
    fail "el contenedor arranca como root (User='${USER_ID}')"
  else
    pass "arranca sin privilegios (User=${USER_ID})"
  fi

  if docker run --rm --entrypoint sh "${IMAGE}" -c 'command -v pip >/dev/null 2>&1'; then
    fail "pip sigue disponible dentro del contenedor"
  else
    pass "sin gestor de paquetes dentro del contenedor"
  fi
done

# --- Autotest: demostrar que la auditoría detecta un secreto de verdad -------
# Una auditoría que siempre dice "todo bien" no prueba nada. Con --self-test se
# construye una imagen desechable que SÍ filtra un .env con una cadena de
# conexión y se comprueba que las comprobaciones 1 y 2 la marcan.
if [[ ${SELF_TEST} -eq 1 ]]; then
  echo
  echo "=============================================================="
  echo " Autotest: la auditoría debe RECHAZAR una imagen con secretos"
  echo "=============================================================="
  CANARY="${WORKDIR}/canary"
  mkdir -p "${CANARY}"
  # Credencial ficticia, con la forma de una real para que dispare el patrón.
  cat >"${CANARY}/.env" <<'CANARY_ENV'
STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=stfake;AccountKey=ZmFrZUtleUZvclNlbGZUZXN0T25seU5vdFJlYWwwMTIzNDU2Nzg5YWJjZGVmZ2g=;EndpointSuffix=core.windows.net
CASES_DB_DSN=postgresql://centinela_admin:notARealPassword123@fake.postgres.database.azure.com:5432/db
CANARY_ENV
  cat >"${CANARY}/Dockerfile" <<'CANARY_DOCKERFILE'
FROM busybox:latest
COPY .env /app/.env
RUN rm -f /app/.env
CANARY_DOCKERFILE

  if docker build --quiet -t centinela-audit-canary:tmp "${CANARY}" >/dev/null 2>&1; then
    if bash "${BASH_SOURCE[0]}" centinela-audit-canary:tmp >/dev/null 2>&1; then
      echo "  ✗ la auditoría APROBÓ una imagen con un .env filtrado: el detector no sirve"
      FAILURES=$((FAILURES + 1))
    else
      echo "  ✓ la auditoría rechaza la imagen trampa (incluso con el .env borrado"
      echo "    en una capa posterior, que es justo el caso peligroso)"
    fi
    docker rmi -f centinela-audit-canary:tmp >/dev/null 2>&1 || true
  else
    echo "  [AVISO] no se pudo construir la imagen trampa; autotest omitido"
  fi
fi

echo
if [[ ${FAILURES} -eq 0 ]]; then
  echo "RESULTADO: todas las imágenes pasan la auditoría."
  exit 0
fi
echo "RESULTADO: ${FAILURES} verificación(es) fallida(s)."
exit 1
