# Especificación Técnica: Almacén de Casos (Azure Relacional Aislado - PostgreSQL)

## 1. Contexto y Objetivos

- **Rol/Componente:** Almacén de datos relacionales para gestión de casos, baja volumetría, alta integridad ACID y trazabilidad inmutable.
- **Proveedor Cloud:** Microsoft Azure (Azure Database for PostgreSQL Flexible Server).
- **Entorno de Red:** Red Virtual (`VNet-Centinela`) con subred delegada aislada (`subnet-db`).
- **Inmutabilidad:** Triggers PL/pgSQL append-only que rechazan cualquier `UPDATE` o `DELETE` sobre las tablas de auditoría y explicaciones.

---

## 2. Formato de Conexión (DSN)

La aplicación backend consume la variable de entorno `CASES_DB_DSN`.

### Formato Estándar PostgreSQL DSN:
```text
postgresql://[usuario]:[contraseña]@[host]:[puerto]/[nombre_bd]
```

### Ejemplos de Conexión:

* **Entorno Local (PostgreSQL local / Docker):**
  ```bash
  export CASES_DB_DSN="postgresql://centinela_admin:secret_password@127.0.0.1:5432/centinela_cases"
  ```

* **Entorno Azure (Red Privada VNet / Subnet-App):**
  ```bash
  export CASES_DB_DSN="postgresql://centinela_admin:<PASSWORD>@psql-centinela-dev.postgres.database.azure.com:5432/centinela_cases?sslmode=require"
  ```

---

## 3. Despliegue Reproducible e Idempotente

El despliegue se ejecuta mediante:
```bash
bash infra/deploy-cases-db.sh
```

- **Idempotencia:** `infra/deploy-cases-db.sh` y `scripts/init-cases-db.sql` se pueden ejecutar de forma repetida sin generar errores (utilizan `CREATE TABLE IF NOT EXISTS`, `ON CONFLICT DO NOTHING`, y `DROP TRIGGER IF EXISTS ... CREATE TRIGGER`).
- **Soporte Local Sin Azure:** Si `CASES_DB_DSN` está definida localmente, el script aplica el DDL directamente mediante `psql` sin requerir credenciales de Azure CLI.

---

## 4. Consultas de Verificación e Inmutabilidad

### 4.1 Verificación de Estructura de Tablas
Para comprobar que las tablas del esquema han sido creadas correctamente:
```sql
SELECT tablename FROM pg_tables WHERE schemaname = 'public';
```
*Tablas esperadas:* `estados`, `casos`, `asignaciones`, `resoluciones`, `auditoria_casos`, `caso_explicaciones`.

### 4.2 Consulta de Verificación de Auditoría
Para consultar la traza de evidencia generada automáticamente por las acciones del sistema:
```sql
SELECT id, entidad, caso_id, accion, estado_nuevo->>'titulo' AS titulo, usuario_accion, fecha_registro 
FROM auditoria_casos 
ORDER BY id DESC;
```

### 4.3 Prueba Real de Inmutabilidad (Rechazo de UPDATE / DELETE)
Ejecutar la siguiente prueba para verificar que el historial no puede ser alterado:

```sql
-- 1. Insertar un caso de prueba
INSERT INTO casos (titulo, descripcion) VALUES ('Caso Prueba Inmutabilidad', 'Evidencia Auditor') RETURNING id;

-- 2. Intentar modificar la traza de auditoría (DEBE FALLAR)
UPDATE auditoria_casos SET accion = 'ALTERADO' WHERE id = 1;
-- Error esperado: RAISE EXCEPTION 'Auditoria es inmutable: Operaciones UPDATE y DELETE estan estrictamente denegadas.'

-- 3. Intentar eliminar la traza de auditoría (DEBE FALLAR)
DELETE FROM auditoria_casos WHERE id = 1;
-- Error esperado: RAISE EXCEPTION 'Auditoria es inmutable: Operaciones UPDATE y DELETE estan estrictamente denegadas.'

-- 4. Intentar modificar la explicación del caso (DEBE FALLAR)
UPDATE caso_explicaciones SET summary = 'ALTERADO' WHERE id = 1;
-- Error esperado: RAISE EXCEPTION 'Auditoria es inmutable: Operaciones UPDATE y DELETE estan estrictamente denegadas.'
```

---

## 5. Script de Validación DoD (Definition of Done)

Para ejecutar la suite de pruebas completa (Bloqueo de red, Inmutabilidad local/remota y Conectividad interna):
```bash
bash scripts/test-cases-db-dod.sh
```

---

## 6. Aprobación QA

- **Responsable QA:** Jorge
- **Criterios Evaluados:**
  - [x] `infra/deploy-cases-db.sh` re-ejecutable sin errores.
  - [x] Reglas de inmutabilidad activas en `auditoria_casos` y `caso_explicaciones`.
  - [x] Formato DSN documentado y ejecutable en local sin cuenta de Azure.
