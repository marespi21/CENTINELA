-- =============================================================================
-- CENTINELA - Especificación DDL para Almacén de Casos (Relacional Aislado)
-- Autor: Juan José Guarín
-- Motor: PostgreSQL (Azure Database for Flexible Server)
-- =============================================================================

-- Habilitar extensión para UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

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
SELECT setval('estados_id_seq', (SELECT MAX(id) FROM estados));

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
