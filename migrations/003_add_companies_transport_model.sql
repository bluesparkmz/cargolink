CREATE TABLE IF NOT EXISTS companies (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    nome_empresa VARCHAR(150) NOT NULL,
    nuit VARCHAR(50),
    numero_licenca VARCHAR(100),
    endereco TEXT,
    cidade VARCHAR(100),
    provincia VARCHAR(100),
    avaliacao_media NUMERIC(3, 2) DEFAULT 0,
    total_viagens INTEGER DEFAULT 0,
    verificada BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

ALTER TABLE drivers
    ADD COLUMN IF NOT EXISTS company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL;

ALTER TABLE vehicles
    ADD COLUMN IF NOT EXISTS company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE;

ALTER TABLE vehicles
    ALTER COLUMN driver_id DROP NOT NULL;

ALTER TABLE load_proposals
    ADD COLUMN IF NOT EXISTS company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE;

ALTER TABLE load_proposals
    ADD COLUMN IF NOT EXISTS vehicle_id INTEGER REFERENCES vehicles(id) ON DELETE SET NULL;

ALTER TABLE load_proposals
    ALTER COLUMN driver_id DROP NOT NULL;

ALTER TABLE trips
    ADD COLUMN IF NOT EXISTS company_id INTEGER REFERENCES companies(id);
