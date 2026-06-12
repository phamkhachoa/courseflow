-- liquibase formatted sql
-- Single consolidated baseline for announcement-service. Merged from the previous
-- 001/002/.../900 changeset files (pre-production cleanup).

-- ============================================================
-- merged from 001-init.sql
-- ============================================================
-- changeset courseflow:announcement-001-init
CREATE TABLE IF NOT EXISTS announcements (
    id UUID PRIMARY KEY,
    course_id UUID NOT NULL,
    author_id VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    audience VARCHAR(40) NOT NULL DEFAULT 'ENROLLED',
    status VARCHAR(40) NOT NULL DEFAULT 'DRAFT',
    publish_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ
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
-- changeset courseflow:announcement-900-demo-data context=demo
INSERT INTO announcements (id, course_id, author_id, title, body, audience, status, published_at)
VALUES
  ('70000000-0000-0000-0000-000000000001', '30000000-0000-0000-0000-000000000001', '2', 'Welcome to CourseFlow v2', 'This course uses announcement, deadline reminder, discussion, search and analytics services.', 'ENROLLED', 'PUBLISHED', NOW())
ON CONFLICT (id) DO NOTHING;
