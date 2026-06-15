-- liquibase formatted sql
-- Single consolidated baseline for gradebook-service. Merged from the previous
-- 001/002/.../900 changeset files (pre-production cleanup).

-- ============================================================
-- merged from 001-init.sql
-- ============================================================
-- changeset courseflow:gradebook-001-init
CREATE TABLE IF NOT EXISTS grade_categories (
    id UUID PRIMARY KEY,
    course_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    weight_percent NUMERIC(5,2) NOT NULL,
    position INT NOT NULL,
    UNIQUE (course_id, name)
);

CREATE TABLE IF NOT EXISTS grade_items (
    id UUID PRIMARY KEY,
    course_id UUID NOT NULL,
    category_id UUID NOT NULL REFERENCES grade_categories(id),
    source_type VARCHAR(60) NOT NULL,
    source_id VARCHAR(120) NOT NULL,
    title VARCHAR(255) NOT NULL,
    max_score NUMERIC(8,2) NOT NULL,
    weight_percent NUMERIC(5,2) NOT NULL,
    published BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (source_type, source_id)
);

CREATE TABLE IF NOT EXISTS grade_entries (
    id UUID PRIMARY KEY,
    grade_item_id UUID NOT NULL REFERENCES grade_items(id),
    student_id VARCHAR(64) NOT NULL,
    raw_score NUMERIC(8,2) NOT NULL,
    adjusted_score NUMERIC(8,2),
    status VARCHAR(40) NOT NULL DEFAULT 'PUBLISHED',
    graded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (grade_item_id, student_id)
);

CREATE TABLE IF NOT EXISTS grade_overrides (
    id UUID PRIMARY KEY,
    grade_entry_id UUID NOT NULL REFERENCES grade_entries(id),
    old_score NUMERIC(8,2) NOT NULL,
    new_score NUMERIC(8,2) NOT NULL,
    reason TEXT NOT NULL,
    actor_id VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rubric_templates (
    id UUID PRIMARY KEY,
    assignment_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    max_score NUMERIC(8,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS rubric_criteria (
    id UUID PRIMARY KEY,
    rubric_template_id UUID NOT NULL REFERENCES rubric_templates(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    max_points NUMERIC(8,2) NOT NULL,
    position INT NOT NULL
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
-- merged from 002-scheme-policies.sql
-- ============================================================
-- changeset courseflow:gradebook-002-scheme-policies
--validCheckSum 9:8cb65be4749490ee9554b2af169fda2e

-- Category aggregation method (WEIGHTED_MEAN | SUM | MEAN) and drop-lowest support
ALTER TABLE grade_categories
    ADD COLUMN IF NOT EXISTS aggregation_method VARCHAR(20) NOT NULL DEFAULT 'WEIGHTED_MEAN',
    ADD COLUMN IF NOT EXISTS drop_lowest INT NOT NULL DEFAULT 0;

-- Per-item late penalty (percent per day of lateness)
ALTER TABLE grade_items
    ADD COLUMN IF NOT EXISTS late_penalty_percent NUMERIC(5,2) NOT NULL DEFAULT 0;

-- Per-entry late metadata + computed letter grade
ALTER TABLE grade_entries
    ADD COLUMN IF NOT EXISTS is_late BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS minutes_late INT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS late_penalty_applied NUMERIC(5,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS letter VARCHAR(5),
    ADD COLUMN IF NOT EXISTS source_event_id VARCHAR(80),
    ADD COLUMN IF NOT EXISTS source_graded_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS version BIGINT NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_grade_overrides_entry_created
    ON grade_overrides (grade_entry_id, created_at DESC);

-- Grading schemes (letter -> percent ranges) scoped to course
CREATE TABLE IF NOT EXISTS grading_schemes (
    id UUID PRIMARY KEY,
    course_id UUID NOT NULL,
    name VARCHAR(120) NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (course_id, name)
);

CREATE TABLE IF NOT EXISTS grading_scheme_entries (
    id UUID PRIMARY KEY,
    scheme_id UUID NOT NULL REFERENCES grading_schemes(id) ON DELETE CASCADE,
    letter VARCHAR(5) NOT NULL,
    min_percent NUMERIC(5,2) NOT NULL,
    gpa_points NUMERIC(4,2),
    position INT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_grading_scheme_entries_scheme
    ON grading_scheme_entries (scheme_id);

-- Partial-unique: at most one default scheme per course (active row).
CREATE UNIQUE INDEX IF NOT EXISTS uq_grading_schemes_default
    ON grading_schemes (course_id) WHERE is_default = TRUE;

-- ============================================================
-- merged from 003-final-grades.sql
-- ============================================================
-- changeset courseflow:gradebook-003-final-grades
--validCheckSum 9:9f8c0dd489d709891d43603a00144945

CREATE TABLE IF NOT EXISTS final_grades (
    id UUID PRIMARY KEY,
    course_id UUID NOT NULL,
    student_id VARCHAR(64) NOT NULL,
    final_score NUMERIC(8,2) NOT NULL,
    letter VARCHAR(5),
    passed BOOLEAN NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'FINALIZED',
    finalized_by VARCHAR(64) NOT NULL,
    finalized_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version BIGINT NOT NULL DEFAULT 0,
    UNIQUE (course_id, student_id)
);

-- ============================================================
-- grade entry source-event tracking for existing databases whose
-- gradebook-002 changeset ran before these columns were introduced.
-- ============================================================
-- changeset courseflow:gradebook-004-grade-entry-source-tracking
ALTER TABLE grade_entries
    ADD COLUMN IF NOT EXISTS source_event_id VARCHAR(80),
    ADD COLUMN IF NOT EXISTS source_graded_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS version BIGINT NOT NULL DEFAULT 0;

-- ============================================================
-- merged from 900-demo-data.sql
-- ============================================================
-- changeset courseflow:gradebook-900-demo-data context=demo
INSERT INTO grade_categories (id, course_id, name, weight_percent, position)
VALUES
  ('a1000000-0000-0000-0000-000000000001', '30000000-0000-0000-0000-000000000001', 'Assignments', 60, 1),
  ('a1000000-0000-0000-0000-000000000002', '30000000-0000-0000-0000-000000000001', 'Quizzes', 30, 2),
  ('a1000000-0000-0000-0000-000000000003', '30000000-0000-0000-0000-000000000001', 'Peer Review', 10, 3)
ON CONFLICT (course_id, name) DO NOTHING;

INSERT INTO grade_items (id, course_id, category_id, source_type, source_id, title, max_score, weight_percent)
VALUES
  ('a2000000-0000-0000-0000-000000000001', '30000000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001', 'ASSIGNMENT', '50000000-0000-0000-0000-000000000001', 'Build service skeleton', 100, 100),
  ('a2000000-0000-0000-0000-000000000002', '30000000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000002', 'QUIZ', 'b3000000-0000-0000-0000-000000000001', 'Microservice boundaries quiz', 20, 100)
ON CONFLICT (source_type, source_id) DO NOTHING;

INSERT INTO grade_entries (id, grade_item_id, student_id, raw_score)
VALUES
  ('a3000000-0000-0000-0000-000000000001', 'a2000000-0000-0000-0000-000000000001', '4', 85)
ON CONFLICT (grade_item_id, student_id) DO NOTHING;

INSERT INTO rubric_templates (id, assignment_id, title, max_score)
VALUES ('a4000000-0000-0000-0000-000000000001', '50000000-0000-0000-0000-000000000001', 'Service skeleton rubric', 100)
ON CONFLICT (id) DO NOTHING;

INSERT INTO rubric_criteria (id, rubric_template_id, name, description, max_points, position)
VALUES
  ('a5000000-0000-0000-0000-000000000001', 'a4000000-0000-0000-0000-000000000001', 'Bounded context clarity', 'Service owns one business capability and no shared domain state.', 40, 1),
  ('a5000000-0000-0000-0000-000000000002', 'a4000000-0000-0000-0000-000000000001', 'Production scaffolding', 'Config, migrations, health checks and package layers are ready.', 60, 2)
ON CONFLICT (id) DO NOTHING;
