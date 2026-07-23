-- =============================================================================
-- CENTINELA - Especificación DDL para Almacén de Casos (Relacional Aislado)
-- Autor: Juan José Guarín
-- Motor: PostgreSQL (Azure Database for Flexible Server)
-- =============================================================================

-- Habilitar extensión para UUIDs si es necesario
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
CREATE TABLE IF NOT EXISTS auditoria_casos (
    id BIGSERIAL PRIMARY KEY,
    caso_id UUID NOT NULL,
    accion VARCHAR(20) NOT NULL CHECK (accion IN ('INSERT', 'UPDATE', 'DELETE')),
    estado_anterior JSONB,
    estado_nuevo JSONB,
    usuario_accion VARCHAR(100) DEFAULT CURRENT_USER,
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
-- Trigger para la generación automática de registros de auditoría al modificar casos
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION audit_casos_change()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        INSERT INTO auditoria_casos (caso_id, accion, estado_anterior, estado_nuevo, usuario_accion)
        VALUES (NEW.id, 'INSERT', NULL, to_jsonb(NEW), CURRENT_USER);
        RETURN NEW;
    ELSIF (TG_OP = 'UPDATE') THEN
        INSERT INTO auditoria_casos (caso_id, accion, estado_anterior, estado_nuevo, usuario_accion)
        VALUES (NEW.id, 'UPDATE', to_jsonb(OLD), to_jsonb(NEW), CURRENT_USER);
        RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
        INSERT INTO auditoria_casos (caso_id, accion, estado_anterior, estado_nuevo, usuario_accion)
        VALUES (OLD.id, 'DELETE', to_jsonb(OLD), NULL, CURRENT_USER);
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
