-- liquibase formatted sql
-- Single consolidated baseline for deadline-service. Merged from the previous
-- 001/002/.../900 changeset files (pre-production cleanup).

-- ============================================================
-- merged from 001-init.sql
-- ============================================================
-- changeset courseflow:deadline-001-init
CREATE TABLE IF NOT EXISTS reminder_policies (
    id UUID PRIMARY KEY,
    course_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    offset_minutes INT NOT NULL,
    channel VARCHAR(40) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS reminder_runs (
    id UUID PRIMARY KEY,
    assignment_id UUID NOT NULL,
    student_id VARCHAR(64) NOT NULL,
    reminder_policy_id UUID NOT NULL REFERENCES reminder_policies(id),
    reminder_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'PENDING',
    version BIGINT NOT NULL DEFAULT 0,
    UNIQUE (assignment_id, student_id, reminder_policy_id)
);

CREATE TABLE IF NOT EXISTS outbox_events (
    id UUID PRIMARY KEY,
    aggregate_id VARCHAR(255) NOT NULL,
    aggregate_type VARCHAR(120) NOT NULL,
    event_type VARCHAR(120) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_outbox_unpublished
    ON outbox_events (created_at, id)
    WHERE published_at IS NULL;

-- ============================================================
-- merged from 900-demo-data.sql
-- ============================================================
-- changeset courseflow:deadline-900-demo-data context=demo
INSERT INTO reminder_policies (id, course_id, name, offset_minutes, channel)
VALUES
  ('60000000-0000-0000-0000-000000000001', '30000000-0000-0000-0000-000000000001', '24h before due date', 1440, 'IN_APP')
ON CONFLICT (id) DO NOTHING;
