-- liquibase formatted sql
-- Single consolidated baseline for live-session-service. Merged from the previous
-- 001/002/.../900 changeset files (pre-production cleanup).

-- ============================================================
-- merged from 001-init.sql
-- ============================================================
-- changeset courseflow:live-session-001-init
CREATE TABLE IF NOT EXISTS live_sessions (
    id UUID PRIMARY KEY,
    course_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    host_id VARCHAR(64) NOT NULL,
    provider VARCHAR(40) NOT NULL DEFAULT 'internal', -- internal, zoom, webrtc
    provider_meeting_id VARCHAR(255),
    scheduled_start TIMESTAMPTZ NOT NULL,
    scheduled_end TIMESTAMPTZ,
    actual_start TIMESTAMPTZ,
    actual_end TIMESTAMPTZ,
    capacity INT,
    status VARCHAR(40) NOT NULL DEFAULT 'SCHEDULED', -- SCHEDULED, LIVE, ENDED, CANCELLED
    recording_storage_key VARCHAR(512),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version BIGINT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS live_session_registrations (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES live_sessions(id),
    user_id VARCHAR(64) NOT NULL,
    registered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    attended BOOLEAN NOT NULL DEFAULT FALSE,
    joined_at TIMESTAMPTZ,
    version BIGINT NOT NULL DEFAULT 0,
    UNIQUE (session_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_live_sessions_course ON live_sessions(course_id);
CREATE INDEX IF NOT EXISTS idx_live_sessions_start ON live_sessions(scheduled_start);

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
-- changeset courseflow:live-session-900-demo context=demo
INSERT INTO live_sessions (id, course_id, title, description, host_id, scheduled_start, scheduled_end, capacity, status)
VALUES (
    '5f1e0a00-0000-4000-8000-000000000001',
    '11111111-1111-4111-8111-111111111111',
    'Live Q&A: Spring Boot Microservices',
    'Weekly live session covering module 3 questions.',
    'instructor-1',
    '2026-06-10T13:00:00Z',
    '2026-06-10T14:00:00Z',
    200,
    'SCHEDULED'
) ON CONFLICT (id) DO NOTHING;

INSERT INTO live_session_registrations (id, session_id, user_id)
VALUES (
    '5f1e0a00-0000-4000-8000-0000000000a1',
    '5f1e0a00-0000-4000-8000-000000000001',
    'student-1'
) ON CONFLICT (session_id, user_id) DO NOTHING;
