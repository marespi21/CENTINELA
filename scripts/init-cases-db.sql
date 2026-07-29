-- =============================================================================
-- CENTINELA - Especificación DDL para Almacén de Casos (Relacional Aislado)
-- Autor: Juan José Guarín
-- Motor: PostgreSQL (Azure Database for Flexible Server)
-- =============================================================================

-- UUIDs: se usa gen_random_uuid() (nativo en PostgreSQL >= 13), por lo que NO se
-- requiere la extensión "uuid-ossp". Azure Database for PostgreSQL no la permite
-- por defecto (no está en la allow-list), así que declararla rompía el DDL.

-- 1. Tabla: estados
CREATE TABLE IF NOT EXISTS estados (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE
);

-- Inserción idempotente de estados por defecto
INSERT INTO estados (id, nombre) VALUES
    (1, 'Abierto'),
    (2, 'En Investigacion'),
    (3, 'Resuelto'),
    (4, 'Cerrado')
ON CONFLICT (nombre) DO NOTHING;

-- Ajuste de secuencia para evitar colisiones futuras en INSERT sin ID explícito
SELECT setval('estados_id_seq', COALESCE((SELECT MAX(id) FROM estados), 1));

-- 2. Tabla: casos
CREATE TABLE IF NOT EXISTS casos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    titulo VARCHAR(150) NOT NULL,
    descripcion TEXT,
    estado_id INT NOT NULL DEFAULT 1 REFERENCES estados(id),
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Tabla: asignaciones
CREATE TABLE IF NOT EXISTS asignaciones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    caso_id UUID NOT NULL REFERENCES casos(id) ON DELETE CASCADE,
    usuario_id UUID NOT NULL,
    asignado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Tabla: resoluciones
CREATE TABLE IF NOT EXISTS resoluciones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    caso_id UUID NOT NULL UNIQUE REFERENCES casos(id) ON DELETE CASCADE,
    detalle TEXT NOT NULL,
    resuelto_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Tabla: auditoria_casos (Append-Only / Inmutable)
-- Registra cambios en casos, asignaciones y resoluciones capturando el usuario real de aplicación
CREATE TABLE IF NOT EXISTS auditoria_casos (
    id BIGSERIAL PRIMARY KEY,
    entidad VARCHAR(50) NOT NULL DEFAULT 'casos',
    caso_id UUID NOT NULL,
    accion VARCHAR(20) NOT NULL CHECK (accion IN ('INSERT', 'UPDATE', 'DELETE')),
    estado_anterior JSONB,
    estado_nuevo JSONB,
    usuario_accion VARCHAR(100) NOT NULL DEFAULT CURRENT_USER,
    fecha_registro TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- Regla de Inmutabilidad para auditoria_casos
-- Bloquea explícitamente cualquier intento de UPDATE o DELETE
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION prevent_audit_tampering()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Auditoria es inmutable: Operaciones UPDATE y DELETE estan estrictamente denegadas.';
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_prevent_audit_tampering ON auditoria_casos;
CREATE TRIGGER trg_prevent_audit_tampering
BEFORE UPDATE OR DELETE ON auditoria_casos
FOR EACH ROW
EXECUTE FUNCTION prevent_audit_tampering();

-- -----------------------------------------------------------------------------
-- Función auxiliar para obtener el usuario de aplicación (evita el harcodeo del login DB)
-- Prioriza la variable de sesión 'app.current_user', si no existe usa CURRENT_USER
-- Ejemplo de uso en app: SET LOCAL app.current_user = 'analista_juan';
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_app_user()
RETURNS VARCHAR(100) AS $$
BEGIN
    RETURN COALESCE(NULLIF(current_setting('app.current_user', true), ''), CURRENT_USER);
END;
$$ LANGUAGE plpgsql;

-- -----------------------------------------------------------------------------
-- Triggers de auditoría completa (casos, asignaciones y resoluciones)
-- -----------------------------------------------------------------------------

-- Auditoría sobre tabla casos
CREATE OR REPLACE FUNCTION audit_casos_change()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        INSERT INTO auditoria_casos (entidad, caso_id, accion, estado_anterior, estado_nuevo, usuario_accion)
        VALUES ('casos', NEW.id, 'INSERT', NULL, to_jsonb(NEW), get_app_user());
        RETURN NEW;
    ELSIF (TG_OP = 'UPDATE') THEN
        INSERT INTO auditoria_casos (entidad, caso_id, accion, estado_anterior, estado_nuevo, usuario_accion)
        VALUES ('casos', NEW.id, 'UPDATE', to_jsonb(OLD), to_jsonb(NEW), get_app_user());
        RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
        INSERT INTO auditoria_casos (entidad, caso_id, accion, estado_anterior, estado_nuevo, usuario_accion)
        VALUES ('casos', OLD.id, 'DELETE', to_jsonb(OLD), NULL, get_app_user());
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_casos ON casos;
CREATE TRIGGER trg_audit_casos
AFTER INSERT OR UPDATE OR DELETE ON casos
FOR EACH ROW
EXECUTE FUNCTION audit_casos_change();

-- Auditoría sobre tabla asignaciones
CREATE OR REPLACE FUNCTION audit_asignaciones_change()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        INSERT INTO auditoria_casos (entidad, caso_id, accion, estado_anterior, estado_nuevo, usuario_accion)
        VALUES ('asignaciones', NEW.caso_id, 'INSERT', NULL, to_jsonb(NEW), get_app_user());
        RETURN NEW;
    ELSIF (TG_OP = 'UPDATE') THEN
        INSERT INTO auditoria_casos (entidad, caso_id, accion, estado_anterior, estado_nuevo, usuario_accion)
        VALUES ('asignaciones', NEW.caso_id, 'UPDATE', to_jsonb(OLD), to_jsonb(NEW), get_app_user());
        RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
        INSERT INTO auditoria_casos (entidad, caso_id, accion, estado_anterior, estado_nuevo, usuario_accion)
        VALUES ('asignaciones', OLD.caso_id, 'DELETE', to_jsonb(OLD), NULL, get_app_user());
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_asignaciones ON asignaciones;
CREATE TRIGGER trg_audit_asignaciones
AFTER INSERT OR UPDATE OR DELETE ON asignaciones
FOR EACH ROW
EXECUTE FUNCTION audit_asignaciones_change();

-- Auditoría sobre tabla resoluciones
CREATE OR REPLACE FUNCTION audit_resoluciones_change()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        INSERT INTO auditoria_casos (entidad, caso_id, accion, estado_anterior, estado_nuevo, usuario_accion)
        VALUES ('resoluciones', NEW.caso_id, 'INSERT', NULL, to_jsonb(NEW), get_app_user());
        RETURN NEW;
    ELSIF (TG_OP = 'UPDATE') THEN
        INSERT INTO auditoria_casos (entidad, caso_id, accion, estado_anterior, estado_nuevo, usuario_accion)
        VALUES ('resoluciones', NEW.caso_id, 'UPDATE', to_jsonb(OLD), to_jsonb(NEW), get_app_user());
        RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
        INSERT INTO auditoria_casos (entidad, caso_id, accion, estado_anterior, estado_nuevo, usuario_accion)
        VALUES ('resoluciones', OLD.caso_id, 'DELETE', to_jsonb(OLD), NULL, get_app_user());
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_resoluciones ON resoluciones;
CREATE TRIGGER trg_audit_resoluciones
AFTER INSERT OR UPDATE OR DELETE ON resoluciones
FOR EACH ROW
EXECUTE FUNCTION audit_resoluciones_change();

-- =============================================================================
-- Semana 3 (módulo Juan José): explicación del caso, persistida e inmutable
-- =============================================================================

-- Vincular el caso con la transacción y la cuenta que lo originaron.
ALTER TABLE casos ADD COLUMN IF NOT EXISTS transaction_id UUID;
ALTER TABLE casos ADD COLUMN IF NOT EXISTS account_id VARCHAR(100);

-- 6. Tabla: caso_explicaciones (Append-Only / Inmutable)
-- Guarda la explicación legible generada por el motor al abrir el caso.
-- `explanation` es el contrato JSON completo (serialize_explanation).
CREATE TABLE IF NOT EXISTS caso_explicaciones (
    id BIGSERIAL PRIMARY KEY,
    caso_id UUID NOT NULL REFERENCES casos(id) ON DELETE CASCADE,
    transaction_id UUID NOT NULL,
    account_id VARCHAR(100) NOT NULL,
    score INT NOT NULL,
    threshold INT NOT NULL,
    is_case BOOLEAN NOT NULL,
    summary TEXT NOT NULL,
    explanation JSONB NOT NULL,
    generado_en TIMESTAMP WITH TIME ZONE NOT NULL,
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_caso_explicaciones_caso ON caso_explicaciones (caso_id);

-- Inmutabilidad: la explicación no se modifica ni se borra (reusa la regla de
-- la auditoría). Solo se permite INSERT.
DROP TRIGGER IF EXISTS trg_prevent_explicacion_tampering ON caso_explicaciones;
CREATE TRIGGER trg_prevent_explicacion_tampering
BEFORE UPDATE OR DELETE ON caso_explicaciones
FOR EACH ROW
EXECUTE FUNCTION prevent_audit_tampering();

-- =============================================================================
-- Semana 5 (módulo Jorge): índice de documentos por caso para la consola
-- =============================================================================

-- 7. Tabla: caso_documentos
-- Vincula un caso con los blobs de sus documentos de verificación, para que la
-- consola pueda LISTARLOS. El acceso al contenido sigue siendo por SAS temporal;
-- aquí solo se guarda la referencia (nunca el contenido del documento).
CREATE TABLE IF NOT EXISTS caso_documentos (
    id BIGSERIAL PRIMARY KEY,
    caso_id UUID NOT NULL REFERENCES casos(id) ON DELETE CASCADE,
    blob_name VARCHAR(255) NOT NULL,
    filename VARCHAR(255),
    content_type VARCHAR(100),
    subido_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (caso_id, blob_name)
);

CREATE INDEX IF NOT EXISTS idx_caso_documentos_caso ON caso_documentos (caso_id);

-- Verificación documental (Sprint 6, Fase 2). Se añade con ALTER en vez de
-- meterlo en el CREATE de arriba para que el script siga siendo idempotente
-- sobre una base ya desplegada: la tabla existe en producción y CREATE TABLE
-- IF NOT EXISTS no la modificaría.
--
-- Nullable a propósito: un documento recién subido aún no está verificado, y
-- los que se subieron antes de esta fase nunca lo estarán.
ALTER TABLE caso_documentos
    ADD COLUMN IF NOT EXISTS veredicto VARCHAR(20),
    ADD COLUMN IF NOT EXISTS verificacion_resumen TEXT,
    ADD COLUMN IF NOT EXISTS verificacion_detalle JSONB,
    ADD COLUMN IF NOT EXISTS verificado_en TIMESTAMP WITH TIME ZONE;

-- Los veredictos posibles los define VerificationVerdict en el dominio. Se
-- restringen también aquí para que un bug de la aplicación no ensucie la tabla
-- con valores que la consola no sabría mostrar.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_caso_documentos_veredicto'
    ) THEN
        ALTER TABLE caso_documentos ADD CONSTRAINT chk_caso_documentos_veredicto
            CHECK (veredicto IS NULL OR veredicto IN
                   ('coincide', 'discrepa', 'insuficiente', 'ilegible'));
    END IF;
END $$;

-- La bandeja querrá filtrar "casos con comprobante que discrepa": es la señal
-- de fraude que esta fase aporta, así que se indexa solo esa condición.
CREATE INDEX IF NOT EXISTS idx_caso_documentos_discrepa
    ON caso_documentos (caso_id) WHERE veredicto = 'discrepa';
