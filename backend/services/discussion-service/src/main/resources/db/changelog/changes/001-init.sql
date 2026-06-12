-- liquibase formatted sql
-- Single consolidated baseline for discussion-service. Merged from the previous
-- 001/002/.../900 changeset files (pre-production cleanup).

-- ============================================================
-- merged from 001-init.sql
-- ============================================================
-- changeset courseflow:discussion-001-init
CREATE TABLE IF NOT EXISTS discussion_threads (
    id UUID PRIMARY KEY,
    course_id UUID NOT NULL,
    assignment_id UUID,
    author_id VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'OPEN',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS discussion_comments (
    id UUID PRIMARY KEY,
    thread_id UUID NOT NULL REFERENCES discussion_threads(id),
    author_id VARCHAR(64) NOT NULL,
    body TEXT NOT NULL,
    accepted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS processed_events (
    event_id UUID PRIMARY KEY,
    consumer_name VARCHAR(120) NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
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
-- changeset courseflow:discussion-900-demo-data context=demo
INSERT INTO discussion_threads (id, course_id, author_id, title)
VALUES
  ('80000000-0000-0000-0000-000000000001', '30000000-0000-0000-0000-000000000001', '4', 'How should I split bounded contexts in v2?')
ON CONFLICT (id) DO NOTHING;
