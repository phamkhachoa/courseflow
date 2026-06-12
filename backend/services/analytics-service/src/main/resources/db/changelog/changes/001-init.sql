-- liquibase formatted sql
-- Single consolidated baseline for analytics-service. Merged from the previous
-- 001/002/.../900 changeset files (pre-production cleanup).

-- ============================================================
-- merged from 001-init.sql
-- ============================================================
-- changeset courseflow:analytics-001-init
CREATE TABLE IF NOT EXISTS course_metrics (
    course_id UUID PRIMARY KEY,
    enrolled_count INT NOT NULL DEFAULT 0,
    submitted_count INT NOT NULL DEFAULT 0,
    average_score NUMERIC(8,2),
    discussion_count INT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version BIGINT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS processed_events (
    event_id UUID PRIMARY KEY,
    consumer_name VARCHAR(120) NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- merged from 002-reporting.sql
-- ============================================================
-- changeset courseflow:analytics-002-reporting
-- Read models for learner/org reporting and course recommendations.
-- These are projections fed by domain events; analytics never owns source-of-truth data.

-- Per-course completion read model.
CREATE TABLE IF NOT EXISTS course_completion_metrics (
    course_id UUID PRIMARY KEY,
    enrolled_count INT NOT NULL DEFAULT 0,
    completed_count INT NOT NULL DEFAULT 0,
    completion_rate NUMERIC(5,2) NOT NULL DEFAULT 0, -- percent 0..100
    avg_days_to_complete NUMERIC(8,2),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Per-student time-spent read model (aggregated minutes by course).
CREATE TABLE IF NOT EXISTS student_time_spent (
    id UUID PRIMARY KEY,
    student_id VARCHAR(64) NOT NULL,
    course_id UUID NOT NULL,
    minutes_spent INT NOT NULL DEFAULT 0,
    last_activity_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (student_id, course_id)
);

CREATE INDEX IF NOT EXISTS idx_time_spent_student ON student_time_spent(student_id);

-- Organization rollup read model for org-admin dashboards.
CREATE TABLE IF NOT EXISTS org_dashboard_metrics (
    org_id VARCHAR(64) PRIMARY KEY,
    active_learners INT NOT NULL DEFAULT 0,
    total_enrollments INT NOT NULL DEFAULT 0,
    avg_completion_rate NUMERIC(5,2) NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Course recommendation read model. score is a precomputed relevance/popularity blend;
-- a real system recomputes this from co-enrollment, ratings and completion signals.
CREATE TABLE IF NOT EXISTS course_recommendations (
    id UUID PRIMARY KEY,
    student_id VARCHAR(64) NOT NULL,
    course_id UUID NOT NULL,
    score NUMERIC(6,3) NOT NULL DEFAULT 0,
    reason VARCHAR(120),
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (student_id, course_id)
);

CREATE INDEX IF NOT EXISTS idx_recommendations_student ON course_recommendations(student_id, score DESC);

-- "Students who took X also took Y" related-course read model for public course pages.
CREATE TABLE IF NOT EXISTS related_courses (
    id UUID PRIMARY KEY,
    course_id UUID NOT NULL,
    related_course_id UUID NOT NULL,
    score NUMERIC(6,3) NOT NULL DEFAULT 0,
    UNIQUE (course_id, related_course_id)
);

CREATE INDEX IF NOT EXISTS idx_related_courses_course ON related_courses(course_id, score DESC);

-- ============================================================
-- merged from 003-engagement.sql
-- ============================================================
-- changeset courseflow:analytics-003-engagement

CREATE TABLE IF NOT EXISTS student_engagement (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id       VARCHAR(64) NOT NULL,
    course_id        UUID NOT NULL,
    engagement_score NUMERIC(5,2) NOT NULL DEFAULT 0,
    login_count_7d   INT NOT NULL DEFAULT 0,
    time_spent_7d    INT NOT NULL DEFAULT 0,
    submissions_7d   INT NOT NULL DEFAULT 0,
    posts_7d         INT NOT NULL DEFAULT 0,
    last_activity_at TIMESTAMPTZ,
    risk_level       VARCHAR(20) NOT NULL DEFAULT 'LOW',
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (student_id, course_id)
);

CREATE INDEX IF NOT EXISTS idx_engagement_course  ON student_engagement(course_id, risk_level);
CREATE INDEX IF NOT EXISTS idx_engagement_student ON student_engagement(student_id);

CREATE TABLE IF NOT EXISTS student_activity_log (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id       VARCHAR(64) NOT NULL,
    course_id        UUID NOT NULL,
    activity_type    VARCHAR(60) NOT NULL,
    duration_minutes INT NOT NULL DEFAULT 0,
    occurred_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_activity_student ON student_activity_log(student_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_activity_course  ON student_activity_log(course_id, occurred_at DESC);

CREATE TABLE IF NOT EXISTS grade_distribution (
    course_id     UUID NOT NULL,
    grade_band    VARCHAR(10) NOT NULL,
    student_count INT NOT NULL DEFAULT 0,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (course_id, grade_band)
);

-- ============================================================
-- merged from 900-demo-data.sql
-- ============================================================
-- changeset courseflow:analytics-900-demo-data context=demo
INSERT INTO course_metrics (course_id, enrolled_count, submitted_count, average_score, discussion_count)
VALUES ('30000000-0000-0000-0000-000000000001', 1, 0, NULL, 1)
ON CONFLICT (course_id) DO NOTHING;
