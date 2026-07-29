-- =============================================================================
-- Migración: verificación documental (Sprint 6, Fase 2)
-- =============================================================================
-- Delta aislado de `init-cases-db.sql` para aplicarlo sobre una base YA
-- desplegada. El script completo también es idempotente, pero recrea los
-- triggers de inmutabilidad (DROP + CREATE), lo que abre una ventana —breve,
-- pero real— en la que la protección anti-manipulación de la auditoría no está
-- activa. Sobre una base en producción no hay motivo para asumir ese riesgo
-- solo para añadir cuatro columnas.
--
-- Estrictamente aditivo: nada se borra, nada se reescribe, y las columnas son
-- nullable porque los documentos subidos antes de esta fase nunca tendrán
-- veredicto.
--
-- Aplicar:  psql "$CASES_DB_DSN" -f scripts/migrations/2026-07-29-verificacion-documental.sql
-- =============================================================================

BEGIN;

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

COMMIT;

-- Comprobación
\d caso_documentos
