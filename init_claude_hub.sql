-- claude_hub: central DB for Claude memory + application data
CREATE DATABASE claude_hub
    WITH ENCODING 'UTF8'
         LC_COLLATE = 'C'
         LC_CTYPE = 'C'
         TEMPLATE = template0;

\c claude_hub

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============ memory schema (mirrors markdown memory) ============
CREATE SCHEMA memory;

CREATE TABLE memory.entries (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name          TEXT NOT NULL,
    description   TEXT NOT NULL,
    type          TEXT NOT NULL CHECK (type IN ('user','feedback','project','reference')),
    body          TEXT NOT NULL,
    source_file   TEXT UNIQUE,         -- markdown filename on disk
    content_hash  TEXT,                 -- sha256 of body, for sync
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX memory_entries_type_idx ON memory.entries(type);
CREATE INDEX memory_entries_name_trgm ON memory.entries USING gin (name gin_trgm_ops);
-- ^ needs pg_trgm; created below if available

CREATE TABLE memory.sync_log (
    id          BIGSERIAL PRIMARY KEY,
    ran_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    direction   TEXT NOT NULL CHECK (direction IN ('md_to_db','db_to_md')),
    entries_added   INT NOT NULL DEFAULT 0,
    entries_updated INT NOT NULL DEFAULT 0,
    entries_removed INT NOT NULL DEFAULT 0,
    notes       TEXT
);

-- ============ apps_shared: cross-application utilities ============
CREATE SCHEMA apps_shared;

CREATE TABLE apps_shared.applications (
    id          SERIAL PRIMARY KEY,
    slug        TEXT UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    root_path   TEXT,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE apps_shared.events (
    id          BIGSERIAL PRIMARY KEY,
    app_id      INT REFERENCES apps_shared.applications(id) ON DELETE CASCADE,
    event_type  TEXT NOT NULL,
    payload     JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX apps_shared_events_app_time_idx ON apps_shared.events(app_id, occurred_at DESC);
CREATE INDEX apps_shared_events_payload_gin ON apps_shared.events USING gin (payload);

-- seed known apps (from user memory)
INSERT INTO apps_shared.applications (slug, name, root_path, description) VALUES
    ('smart_agent',      'SmartAgent',           'C:\Users\Cyd_L\Documents\Claude\SmartAgent',        'Self-evolving Python agent'),
    ('medical_records',  'MedicalRecordsApp',    'C:\Users\Cyd_L\Documents\Claude\MedicalRecordsApp', 'HIPAA-compliant medical records platform')
ON CONFLICT (slug) DO NOTHING;

-- ============ per-application schemas (empty namespaces) ============
CREATE SCHEMA smart_agent;
COMMENT ON SCHEMA smart_agent IS 'SmartAgent application data';

CREATE SCHEMA medical_records;
COMMENT ON SCHEMA medical_records IS 'MedicalRecordsApp - HIPAA-sensitive. Enable audit logging and encryption before storing PHI.';

-- ============ dedicated app user (non-superuser) ============
CREATE ROLE claude_app WITH LOGIN PASSWORD 'change_me_after_first_use';
GRANT CONNECT ON DATABASE claude_hub TO claude_app;
GRANT USAGE, CREATE ON SCHEMA memory, apps_shared, smart_agent, medical_records TO claude_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA memory, apps_shared, smart_agent, medical_records
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO claude_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA memory, apps_shared, smart_agent, medical_records
    GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO claude_app;
