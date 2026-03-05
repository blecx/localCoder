-- Hub initial schema

CREATE TABLE IF NOT EXISTS tasks (
    id          SERIAL PRIMARY KEY,
    repo_url    TEXT        NOT NULL,
    branch      TEXT        NOT NULL DEFAULT 'main',
    description TEXT        NOT NULL,
    status      TEXT        NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending','claimed','running','done','failed')),
    claimed_by  TEXT,
    result      TEXT,
    patch       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS artifacts (
    id          SERIAL PRIMARY KEY,
    task_id     INTEGER     NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    name        TEXT        NOT NULL,
    path        TEXT        NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Automatically update updated_at on row change
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tasks_updated_at ON tasks;
CREATE TRIGGER tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
