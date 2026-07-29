#!/usr/bin/env bash
# =============================================================================
# CENTINELA — Compila los cierres pinneados de dependencias por imagen
# =============================================================================
# Resuelve requirements-{api,worker}.in a un requirements-{api,worker}.txt con
# TODAS las dependencias (directas y transitivas) fijadas a una versión exacta,
# para que reconstruir una imagen dé el mismo resultado meses después.
#
# La resolución corre DENTRO del contenedor base de destino (linux/amd64,
# python:3.12-slim): resolver en macOS elegiría wheels de la plataforma
# equivocada y el pin sería mentira.
#
# Uso:  bash infra/compile-requirements.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${SCRIPT_DIR}/../backend"
PYTHON_BASE="${PYTHON_BASE:-python:3.12-slim}"

for TARGET in api worker; do
  echo "==> Compilando requirements-${TARGET}.txt (${PYTHON_BASE}, linux/amd64)"
  docker run --rm --platform linux/amd64 \
    -v "${BACKEND_DIR}:/work" -w /work \
    "${PYTHON_BASE}" \
    sh -c "pip install --quiet --no-cache-dir pip-tools && \
           pip-compile --quiet --no-header --strip-extras \
             --output-file=requirements-${TARGET}.txt requirements-${TARGET}.in"
done

echo
echo "Listo. Paquetes resueltos:"
for TARGET in api worker; do
  printf '  %-8s %s paquetes\n' "${TARGET}" \
    "$(grep -cE '^[a-zA-Z0-9]' "${BACKEND_DIR}/requirements-${TARGET}.txt")"
done
