-- liquibase formatted sql
-- Single consolidated baseline for assignment-service. Merged from the previous
-- 001/002/.../900 changeset files (pre-production cleanup).

-- ============================================================
-- merged from 001-init.sql
-- ============================================================
-- changeset courseflow:assignment-001-init
CREATE TABLE IF NOT EXISTS assignments (
    id UUID PRIMARY KEY,
    course_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    assignment_type VARCHAR(60) NOT NULL,
    due_at TIMESTAMPTZ NOT NULL,
    max_score NUMERIC(8,2) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'DRAFT'
);

CREATE TABLE IF NOT EXISTS submissions (
    id UUID PRIMARY KEY,
    assignment_id UUID NOT NULL REFERENCES assignments(id),
    student_id VARCHAR(64) NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'SUBMITTED',
    UNIQUE (assignment_id, student_id)
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
-- merged from 002-submission-attachments.sql
-- ============================================================
-- changeset courseflow:assignment-002-submission-attachments
--validCheckSum 9:1cf1fc3765ef21ace1b7f3cdf02381cc
CREATE TABLE IF NOT EXISTS submission_attachments (
    id UUID PRIMARY KEY,
    submission_id UUID NOT NULL REFERENCES submissions(id),
    media_asset_id VARCHAR(64),
    file_name VARCHAR(255) NOT NULL,
    storage_key VARCHAR(512) NOT NULL,
    content_type VARCHAR(120),
    size_bytes BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_submission_attachments_submission
    ON submission_attachments (submission_id);

-- ============================================================
-- merged from 004-attachment-upload-grants.sql
-- ============================================================
-- changeset courseflow:assignment-004-attachment-upload-grants
-- Upload grants bind object-storage keys to the authenticated learner who requested them.
-- Submissions may only reference an unconsumed grant for the same assignment/student.
CREATE TABLE IF NOT EXISTS attachment_upload_grants (
    id UUID PRIMARY KEY,
    assignment_id UUID NOT NULL REFERENCES assignments(id),
    student_id VARCHAR(64) NOT NULL,
    storage_key VARCHAR(512) NOT NULL UNIQUE,
    file_name VARCHAR(255) NOT NULL,
    content_type VARCHAR(120),
    size_bytes BIGINT,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    consumed_at TIMESTAMPTZ,
    submission_id UUID REFERENCES submissions(id)
);

CREATE INDEX IF NOT EXISTS idx_attachment_upload_grants_owner
    ON attachment_upload_grants (assignment_id, student_id, storage_key);

-- ============================================================
-- merged from 003-thicken-assignments.sql
-- ============================================================
-- changeset courseflow:assignment-003-thicken

-- Submission types + dates + multi-attempt + late policy + rubric link
ALTER TABLE assignments
    ADD COLUMN IF NOT EXISTS instructions TEXT,
    ADD COLUMN IF NOT EXISTS available_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS lock_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS submission_types VARCHAR(120) NOT NULL DEFAULT 'FILE',
    ADD COLUMN IF NOT EXISTS max_attempts INT NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS allow_resubmission BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS late_penalty_percent NUMERIC(5,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS late_penalty_interval VARCHAR(10) NOT NULL DEFAULT 'DAY',
    ADD COLUMN IF NOT EXISTS late_penalty_max_percent NUMERIC(5,2) NOT NULL DEFAULT 100,
    ADD COLUMN IF NOT EXISTS rubric_id UUID;

-- Drop old unique to enable multi-attempt
ALTER TABLE submissions DROP CONSTRAINT IF EXISTS submissions_assignment_id_student_id_key;

ALTER TABLE submissions
    ADD COLUMN IF NOT EXISTS attempt_no INT NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS submission_text TEXT,
    ADD COLUMN IF NOT EXISTS submission_url VARCHAR(2048),
    ADD COLUMN IF NOT EXISTS is_late BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS minutes_late INT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS raw_score NUMERIC(8,2),
    ADD COLUMN IF NOT EXISTS late_penalty_applied NUMERIC(5,2),
    ADD COLUMN IF NOT EXISTS final_score NUMERIC(8,2),
    ADD COLUMN IF NOT EXISTS graded_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS grader_id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS feedback TEXT,
    ADD COLUMN IF NOT EXISTS version BIGINT NOT NULL DEFAULT 0;

CREATE UNIQUE INDEX IF NOT EXISTS uq_submissions_assignment_student_attempt
    ON submissions (assignment_id, student_id, attempt_no);

-- Local rubric snapshot (one per assignment)
CREATE TABLE IF NOT EXISTS assignment_rubrics (
    id UUID PRIMARY KEY,
    assignment_id UUID NOT NULL UNIQUE REFERENCES assignments(id),
    title VARCHAR(255) NOT NULL,
    max_score NUMERIC(8,2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS assignment_rubric_criteria (
    id UUID PRIMARY KEY,
    rubric_id UUID NOT NULL REFERENCES assignment_rubrics(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    max_points NUMERIC(8,2) NOT NULL,
    position INT NOT NULL
);

CREATE TABLE IF NOT EXISTS submission_rubric_scores (
    id UUID PRIMARY KEY,
    submission_id UUID NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    criterion_id UUID NOT NULL REFERENCES assignment_rubric_criteria(id),
    points NUMERIC(8,2) NOT NULL,
    comment TEXT,
    UNIQUE (submission_id, criterion_id)
);

CREATE TABLE IF NOT EXISTS processed_events (
    event_id UUID PRIMARY KEY,
    consumer_name VARCHAR(120) NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- merged from 900-demo-data.sql
-- ============================================================
-- changeset courseflow:assignment-900-demo-data context=demo
INSERT INTO assignments (id, course_id, title, assignment_type, due_at, max_score, status)
VALUES
  ('50000000-0000-0000-0000-000000000001', '30000000-0000-0000-0000-000000000001', 'Build service skeleton', 'CODE_PROJECT', '2026-02-10T23:59:00+07:00', 100, 'PUBLISHED')
ON CONFLICT (id) DO NOTHING;
