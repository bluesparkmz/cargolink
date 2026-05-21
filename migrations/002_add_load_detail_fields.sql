-- Campos do ecrã Detalhes da Carga (PostgreSQL)

ALTER TABLE loads
    ADD COLUMN IF NOT EXISTS tipo_carga_volume VARCHAR(30),
    ADD COLUMN IF NOT EXISTS tipo_veiculo_sugerido VARCHAR(150);
