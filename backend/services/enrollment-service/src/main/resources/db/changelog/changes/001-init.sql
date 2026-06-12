-- liquibase formatted sql
-- Single consolidated baseline for enrollment-service. Merged from the previous
-- 001/002/.../900 changeset files (pre-production cleanup).

-- ============================================================
-- merged from 001-init.sql
-- ============================================================
-- changeset courseflow:enrollment-001-init
CREATE TABLE IF NOT EXISTS enrollments (
    id UUID PRIMARY KEY,
    student_id VARCHAR(64) NOT NULL,
    course_id UUID NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'ACTIVE',
    enrolled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (student_id, course_id)
);

CREATE TABLE IF NOT EXISTS waitlist_entries (
    id UUID PRIMARY KEY,
    student_id VARCHAR(64) NOT NULL,
    course_id UUID NOT NULL,
    position INT NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'WAITING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (student_id, course_id)
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
-- merged from 002-status-workflow.sql
-- ============================================================
-- changeset courseflow:enrollment-002-status-workflow

ALTER TABLE enrollments
    ADD COLUMN IF NOT EXISTS section_id    UUID,
    ADD COLUMN IF NOT EXISTS dropped_at    TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS completed_at  TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS drop_reason   TEXT,
    ADD COLUMN IF NOT EXISTS dropped_by    VARCHAR(64),
    ADD COLUMN IF NOT EXISTS version       BIGINT NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS enrollment_audit_log (
    id            UUID PRIMARY KEY,
    enrollment_id UUID NOT NULL,
    actor_id      VARCHAR(64) NOT NULL,
    action        VARCHAR(60) NOT NULL,
    old_status    VARCHAR(40),
    new_status    VARCHAR(40),
    reason        TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_enrollment ON enrollment_audit_log(enrollment_id);
CREATE INDEX IF NOT EXISTS idx_audit_actor      ON enrollment_audit_log(actor_id);

-- ============================================================
-- merged from 003-capacity-waitlist.sql
-- ============================================================
-- changeset courseflow:enrollment-003-capacity-waitlist

-- Per-course capacity owned by enrollment-service (per-service DB; we do NOT reach into
-- organization-service's course_sections). A missing row OR a NULL capacity means "unlimited".
CREATE TABLE IF NOT EXISTS course_capacity (
    course_id  UUID PRIMARY KEY,
    capacity   INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Track when a waitlist entry was promoted to an active enrollment.
ALTER TABLE waitlist_entries
    ADD COLUMN IF NOT EXISTS promoted_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS version BIGINT NOT NULL DEFAULT 0;

ALTER TABLE course_capacity
    ADD COLUMN IF NOT EXISTS version BIGINT NOT NULL DEFAULT 0;

-- Stop two concurrent WAITING joins from grabbing the same FIFO position for a course.
CREATE UNIQUE INDEX IF NOT EXISTS uq_waitlist_course_position
    ON waitlist_entries (course_id, position)
    WHERE status = 'WAITING';

-- ============================================================
-- merged from 004-processed-events.sql
-- ============================================================
-- changeset courseflow:enrollment-004-processed-events

-- Dedup table for the idempotent course.completed consumer. The (event_id) primary key plus an
-- ON CONFLICT DO NOTHING insert guarantees each event is processed at most once per consumer.
CREATE TABLE IF NOT EXISTS processed_events (
    event_id      UUID PRIMARY KEY,
    consumer_name VARCHAR(120) NOT NULL,
    processed_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- merged from 900-demo-data.sql
-- ============================================================
-- changeset courseflow:enrollment-900-demo-data context=demo
INSERT INTO enrollments (id, student_id, course_id)
VALUES ('40000000-0000-0000-0000-000000000001', '4', '30000000-0000-0000-0000-000000000001')
ON CONFLICT (student_id, course_id) DO NOTHING;
