# Especificación Técnica: Almacén de Casos (Azure Relacional Aislado)

## 1. Contexto y Objetivos

- **Rol/Componente:** Almacén de datos relacionales para gestión de casos, baja volumetría, alta integridad ACID y trazabilidad inmutable.
- **Proveedor Cloud:** Microsoft Azure (Capa Gratuita / Free Tier).
- **Entorno de Red:** Red Virtual (VNet) con topología de subredes aisladas.

## 2. Stack Tecnológico Preferido

- **Motor BD:** PostgreSQL (Azure Database for Flexible Server / VM en Free Tier) o Azure SQL Database.
- **Seguridad de Red:** Azure Virtual Network (VNet), Subredes (`Subnet-App`, `Subnet-DB`), Network Security Group (NSG).
- **Inmutabilidad:** Reglas SQL (`RULES`) / Triggers Append-Only y esquemas restringidos.

## 3. Especificación del Modelo de Datos (DDL)

### Entidades Principales

- **`casos`**: `id` (UUID PK), `titulo` (VARCHAR 150), `descripcion` (TEXT), `creado_en` (TIMESTAMP).
- **`estados`**: `id` (SERIAL/INT PK), `nombre` (VARCHAR 50 UNIQUE).
- **`asignaciones`**: `id` (UUID PK), `caso_id` (FK -> `casos`), `usuario_id` (UUID), `asignado_en` (TIMESTAMP).
- **`resoluciones`**: `id` (UUID PK), `caso_id` (FK UNIQUE -> `casos`), `detalle` (TEXT), `resuelto_en` (TIMESTAMP).

### Entidad de Auditoría (Inmutable / Append-Only)

- **`auditoria_casos`**:
  - `id` (BIGSERIAL / BIGINT PK)
  - `caso_id` (UUID)
  - `accion` (VARCHAR 20: `INSERT`, `UPDATE`, `DELETE`)
  - `estado_anterior` (JSONB / NVARCHAR)
  - `estado_nuevo` (JSONB / NVARCHAR)
  - `usuario_accion` (VARCHAR 100)
  - `fecha_registro` (TIMESTAMP DEFAULT NOW())
  - **Regla de Inmutabilidad:** Bloqueo explícito de operaciones `UPDATE` y `DELETE` mediante reglas o triggers (`DO INSTEAD NOTHING` / Exception).

## 4. Configuración de Red y Aislamiento (Azure NSG)

- **Visibilidad Externa:** `Public Network Access = Disabled`. Sin IP pública directa.
- **Topología de Red:**
  - `VNet-Centinela` (o VNet principal).
  - `Subnet-App`: Aloja el backend/API.
  - `Subnet-DB` (o `Subnet-Storage`): Subred delegada para la BD.
- **Reglas del Network Security Group (NSG) en `Subnet-DB`:**
  - **Inbound Rule 1 (`Allow-App-To-DB`):**
    - Source: CIDR de `Subnet-App` (o Tag `VirtualNetwork`).
    - Destination Port: 5432 (PostgreSQL) / 1433 (SQL Server).
    - Protocol: TCP.
    - Action: Allow.
  - **Inbound Rule 2 (`Deny-Internet-All`):**
    - Source: Internet (`0.0.0.0/0`).
    - Destination Port: `*`.
    - Action: Deny (Prioridad alta).

## 5. Definición de Respaldo y Continuidad (Free Tier)

- **Estrategia:** Automated Daily Backups de Azure.
- **Frecuencia:** Diaria (Automática).
- **Retención:** 7 días (Límite estándar gratuito).
- **RPO (Recovery Point Objective):** < 5 minutos (aprovechando Point-In-Time Restore / Logs WAL).
- **RTO (Recovery Time Objective):** < 30 minutos (Tiempo de restauración de la instancia).

## 6. Criterios de Aceptación y Pruebas (DoD)

- **Script SQL:** Código DDL ejecutable con constraints de llaves foráneas y reglas de inmutabilidad en la tabla de auditoría.
- **Prueba de Bloqueo Externo (Evidencia 1):** Comando de red (`nc`, `Test-NetConnection` o `psql`) ejecutado desde una máquina en Internet que resuelto en `Connection timed out` o `Connection refused`.
- **Prueba de Conexión Interna (Evidencia 2):** Conexión exitosa desde la subred de aplicación (`Subnet-App`).
- **Documentación:** Resumen formal de arquitectura listo para enviar a revisión.
