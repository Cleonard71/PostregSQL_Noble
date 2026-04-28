-- Migration: add apps_shared.files table for tracking files stored on disk
-- Run after init_claude_hub.sql

\c claude_hub

CREATE TABLE IF NOT EXISTS apps_shared.files (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    app_id        INT REFERENCES apps_shared.applications(id) ON DELETE SET NULL,
    original_name TEXT NOT NULL,
    stored_path   TEXT NOT NULL,
    mime_type     TEXT,
    size_bytes    BIGINT,
    description   TEXT,
    tags          TEXT[],
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS files_app_idx  ON apps_shared.files(app_id);
CREATE INDEX IF NOT EXISTS files_tags_idx ON apps_shared.files USING gin(tags);

-- Add 'shared' application if not present (for files not tied to a specific app)
INSERT INTO apps_shared.applications (slug, name, description) VALUES
    ('shared', 'Shared', 'Cross-app file storage namespace')
ON CONFLICT (slug) DO NOTHING;

-- Re-grant permissions on all existing objects (default privileges only apply to new ones)
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA memory, apps_shared, smart_agent, medical_records TO claude_app;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA memory, apps_shared, smart_agent, medical_records TO claude_app;

COMMENT ON TABLE apps_shared.files IS 'Tracks files stored on disk. Disk path stored in stored_path; physical files live in Files/<app_slug>/.';
