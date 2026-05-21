-- Executar uma vez se a BD já existia antes das colunas de localização.
-- PostgreSQL

ALTER TABLE drivers
    ADD COLUMN IF NOT EXISTS latitude_atual NUMERIC(10, 7),
    ADD COLUMN IF NOT EXISTS longitude_atual NUMERIC(10, 7),
    ADD COLUMN IF NOT EXISTS location_updated_at TIMESTAMP;

ALTER TABLE vehicles
    ADD COLUMN IF NOT EXISTS latitude_atual NUMERIC(10, 7),
    ADD COLUMN IF NOT EXISTS longitude_atual NUMERIC(10, 7),
    ADD COLUMN IF NOT EXISTS location_updated_at TIMESTAMP;
