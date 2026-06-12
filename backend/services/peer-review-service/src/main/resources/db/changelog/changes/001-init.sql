-- liquibase formatted sql
-- Single consolidated baseline for peer-review-service. Merged from the previous
-- 001/002/.../900 changeset files (pre-production cleanup).

-- ============================================================
-- merged from 001-init.sql
-- ============================================================
-- changeset courseflow:peer-review-001-init
CREATE TABLE IF NOT EXISTS peer_review_settings (
    id UUID PRIMARY KEY,
    assignment_id UUID NOT NULL,
    reviewers_per_submission INT NOT NULL,
    anonymous BOOLEAN NOT NULL DEFAULT TRUE,
    review_due_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'ACTIVE',
    UNIQUE (assignment_id)
);

CREATE TABLE IF NOT EXISTS review_forms (
    id UUID PRIMARY KEY,
    assignment_id UUID NOT NULL,
    rubric_template_id UUID,
    instructions TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS review_assignments (
    id UUID PRIMARY KEY,
    course_id UUID,
    assignment_id UUID NOT NULL,
    submission_id UUID NOT NULL,
    reviewer_id VARCHAR(64) NOT NULL,
    reviewee_id VARCHAR(64) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'ASSIGNED',
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (submission_id, reviewer_id)
);

CREATE TABLE IF NOT EXISTS review_submissions (
    id UUID PRIMARY KEY,
    review_assignment_id UUID NOT NULL REFERENCES review_assignments(id),
    score NUMERIC(8,2) NOT NULL,
    comment TEXT NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status VARCHAR(40) NOT NULL DEFAULT 'SUBMITTED'
);

CREATE TABLE IF NOT EXISTS review_disputes (
    id UUID PRIMARY KEY,
    review_submission_id UUID NOT NULL REFERENCES review_submissions(id),
    opened_by VARCHAR(64) NOT NULL,
    reason TEXT NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'OPEN',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS peer_review_results (
    id UUID PRIMARY KEY,
    submission_id UUID NOT NULL,
    final_score NUMERIC(8,2) NOT NULL,
    finalized_by VARCHAR(64) NOT NULL,
    finalized_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version BIGINT NOT NULL DEFAULT 0,
    UNIQUE (submission_id)
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
-- changeset courseflow:peer-review-900-demo-data context=demo
INSERT INTO peer_review_settings (id, assignment_id, reviewers_per_submission, anonymous, review_due_at)
VALUES ('d1000000-0000-0000-0000-000000000001', '50000000-0000-0000-0000-000000000001', 2, TRUE, '2026-02-15T23:59:00+07:00')
ON CONFLICT (assignment_id) DO NOTHING;

INSERT INTO review_forms (id, assignment_id, rubric_template_id, instructions)
VALUES ('d2000000-0000-0000-0000-000000000001', '50000000-0000-0000-0000-000000000001', 'a4000000-0000-0000-0000-000000000001', 'Review service boundaries, package layers and production readiness.')
ON CONFLICT (id) DO NOTHING;
