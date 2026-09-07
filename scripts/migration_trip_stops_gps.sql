-- =============================================================================
-- Migration: adicionar GPS e resumed_at a tabela trip_stops
-- Data: 2026-09-07
-- =============================================================================

-- Adicionar coluna latitude (opcional - onde o motorista parou)
ALTER TABLE trip_stops
    ADD COLUMN IF NOT EXISTS latitude NUMERIC(10, 7);

-- Adicionar coluna longitude (opcional - onde o motorista parou)
ALTER TABLE trip_stops
    ADD COLUMN IF NOT EXISTS longitude NUMERIC(10, 7);

-- Adicionar coluna resumed_at (opcional - quando o motorista retomou a viagem)
ALTER TABLE trip_stops
    ADD COLUMN IF NOT EXISTS resumed_at TIMESTAMP;

-- =============================================================================
-- Verificacao
-- =============================================================================
-- SELECT column_name, data_type
-- FROM information_schema.columns
-- WHERE table_name = 'trip_stops'
-- ORDER BY ordinal_position;
