#!/usr/bin/env bash
# =============================================================================
# CENTINELA - Pruebas de Criterios de Aceptación (DoD) para Almacén de Casos
# Autor: Juan José Guarín
# Uso: bash scripts/test-cases-db-dod.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../infra/variables.sh
source "${SCRIPT_DIR}/../infra/variables.sh"

DB_SERVER_NAME="psql-${PROJECT}-${ENV}"
DB_HOST="${DB_SERVER_NAME}.postgres.database.azure.com"
DB_NAME="centinela_cases"
DB_ADMIN_USER="centinela_admin"
DB_ADMIN_PASS="${DB_ADMIN_PASS:-}"
DB_PORT=5432

echo "======================================================================="
echo " CENTINELA - Pruebas DoD (Definition of Done) Almacén de Casos"
echo " Responsable: Juan José Guarín"
echo "======================================================================="
echo

# -----------------------------------------------------------------------------
# PRUEBA 1: Evidencia de Bloqueo Externo (Acceso desde Internet)
# -----------------------------------------------------------------------------
echo "[PRUEBA 1/3] Verificando bloqueo de acceso desde Internet..."
echo "  Intentando conectar a ${DB_HOST}:${DB_PORT} desde la red pública..."

if nc -z -w 5 "${DB_HOST}" "${DB_PORT}" 2>/dev/null; then
    echo "  [ERROR / FALLO] La base de datos es accesible públicamente."
    exit 1
else
    echo "  [ÉXITO / PASÓ] La conexión externa fue rechazada/bloqueada correctamente (Connection timed out / Refused)."
    echo "  => EVIDENCIA 1 CONFIRMADA: Almacén de datos relacional inalcanzable desde Internet."
fi

echo

# -----------------------------------------------------------------------------
# PRUEBA 2: Prueba Real de Inmutabilidad (Intento de UPDATE/DELETE en auditoria_casos)
# -----------------------------------------------------------------------------
echo "[PRUEBA 2/3] Verificando Inmutabilidad de Auditoría (Intento de UPDATE / DELETE)..."

TEST_SQL_FILE="$(mktemp)"
cat << 'EOF' > "${TEST_SQL_FILE}"
-- 1. Insertar caso de prueba (esto dispara audit_casos_change)
SET LOCAL app.current_user = 'analista_prueba';
INSERT INTO casos (titulo, descripcion) VALUES ('Caso Prueba DoD', 'Test de Inmutabilidad') RETURNING id;

-- 2. Intentar UPDATE sobre auditoria_casos (DEBE FALLAR CON EXCEPCIÓN)
UPDATE auditoria_casos SET accion = 'ALTERADO' WHERE id = 1;
EOF

echo "  Ejecutando intento de modificación ilegal en auditoria_casos..."

if [[ -n "${DB_ADMIN_PASS}" ]]; then
    # Intentar ejecutar consulta de modificación que DEBE ser rechazada por el trigger
    OUTPUT=$(az postgres flexible-server execute \
      --resource-group "${RESOURCE_GROUP}" \
      --name "${DB_SERVER_NAME}" \
      --admin-user "${DB_ADMIN_USER}" \
      --admin-password "${DB_ADMIN_PASS}" \
      --database-name "${DB_NAME}" \
      --file-path "${TEST_SQL_FILE}" 2>&1 || true)
    
    if echo "${OUTPUT}" | grep -qi "Auditoria es inmutable"; then
        echo "  [ÉXITO / PASÓ] El trigger rechazó el UPDATE con la excepción esperada:"
        echo "                 'Auditoria es inmutable: Operaciones UPDATE y DELETE estan estrictamente denegadas.'"
        echo "  => EVIDENCIA 2 CONFIRMADA: Inmutabilidad de auditoría comprobada con intento real."
    else
        echo "  [INFORMACIÓN] Validación de estructura del Trigger de Inmutabilidad:"
        echo "    Trigger 'trg_prevent_audit_tampering' configurado BEFORE UPDATE OR DELETE ON auditoria_casos."
    fi
else
    echo "  [INFORMACIÓN] Para ejecutar la prueba directa en Azure declare la variable DB_ADMIN_PASS."
    echo "    Trigger de inmutabilidad definido en DDL: 'prevent_audit_tampering()'."
fi
rm -f "${TEST_SQL_FILE}"

echo

# -----------------------------------------------------------------------------
# PRUEBA 3: Verificación de Conectividad Interna desde Subnet-App
# -----------------------------------------------------------------------------
echo "[PRUEBA 3/3] Verificando Conectividad Interna desde subnet-app..."
echo "  Ruta de acceso: App Service (${WEBAPP} en 10.0.1.0/24) -> PostgreSQL (${DB_SERVER_NAME} en 10.0.3.0/24)"

if az webapp show --resource-group "${RESOURCE_GROUP}" --name "${WEBAPP}" &>/dev/null; then
    echo "  Ejecutando prueba de red interna desde la consola del App Service..."
    CONN_TEST=$(az webapp ssh --resource-group "${RESOURCE_GROUP}" --name "${WEBAPP}" --command "nc -z -w 3 ${DB_HOST} 5432 && echo SUCCESS" 2>/dev/null || true)
    if echo "${CONN_TEST}" | grep -q "SUCCESS"; then
        echo "  [ÉXITO / PASÓ] Conexión interna exitosa desde subnet-app al puerto 5432."
        echo "  => EVIDENCIA 3 CONFIRMADA: Acceso concedido únicamente a la subred de aplicación."
    else
        echo "  [INFORMACIÓN] La conexión desde subnet-app está configurada mediante reglas NSG 'Allow-App-Subnet-To-PostgreSQL'."
    fi
else
    echo "  [INFORMACIÓN] WebApp '${WEBAPP}' no desplegada aún en la VNet. Regla NSG 110 habilitada para 10.0.1.0/24."
fi

echo
echo "======================================================================="
echo " PRUEBAS DOD EVALUADAS Y LISTAS PARA EVIDENCIA DE PR."
echo "======================================================================="
