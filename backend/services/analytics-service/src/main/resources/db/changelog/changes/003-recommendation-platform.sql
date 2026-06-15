-- liquibase formatted sql
-- changeset courseflow:analytics-003-recommendation-platform
ALTER TABLE related_courses
    ADD COLUMN IF NOT EXISTS source VARCHAR(60) NOT NULL DEFAULT 'BEHAVIORAL',
    ADD COLUMN IF NOT EXISTS reason VARCHAR(160),
    ADD COLUMN IF NOT EXISTS reason_code VARCHAR(80),
    ADD COLUMN IF NOT EXISTS model_version VARCHAR(80),
    ADD COLUMN IF NOT EXISTS generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_related_courses_source
    ON related_courses(course_id, source, score DESC);

CREATE TABLE IF NOT EXISTS manual_related_courses (
    id UUID PRIMARY KEY,
    course_id UUID NOT NULL,
    related_course_id UUID NOT NULL,
    placement VARCHAR(60) NOT NULL DEFAULT 'COURSE_DETAIL',
    position INT NOT NULL DEFAULT 0,
    weight NUMERIC(6,3) NOT NULL DEFAULT 1,
    reason VARCHAR(160),
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    effective_from TIMESTAMPTZ,
    effective_to TIMESTAMPTZ,
    created_by VARCHAR(120),
    updated_by VARCHAR(120),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT chk_manual_related_not_self CHECK (course_id <> related_course_id),
    CONSTRAINT ux_manual_related_course_pair UNIQUE (course_id, related_course_id, placement)
);

CREATE INDEX IF NOT EXISTS idx_manual_related_course_active
    ON manual_related_courses(course_id, status, placement, position, weight DESC);

CREATE TABLE IF NOT EXISTS recommendation_tracking_events (
    event_id UUID PRIMARY KEY,
    event_type VARCHAR(60) NOT NULL,
    source VARCHAR(60) NOT NULL,
    course_id UUID,
    related_course_id UUID,
    student_id VARCHAR(64),
    session_id VARCHAR(120),
    placement VARCHAR(60) NOT NULL DEFAULT 'COURSE_DETAIL',
    reason_code VARCHAR(80),
    recommendation_source VARCHAR(60),
    model_version VARCHAR(80),
    attribution_id VARCHAR(120),
    occurred_at TIMESTAMPTZ NOT NULL,
    metadata_json TEXT,
    request_hash VARCHAR(96) NOT NULL,
    actor_id VARCHAR(120),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_recommendation_tracking_event_type CHECK (
        event_type IN ('IMPRESSION', 'CLICK', 'ENROLLMENT')
    ),
    CONSTRAINT chk_recommendation_tracking_identity CHECK (
        student_id IS NOT NULL OR session_id IS NOT NULL OR actor_id IS NOT NULL
    ),
    CONSTRAINT chk_recommendation_tracking_not_self CHECK (
        related_course_id IS NULL OR course_id IS NULL OR course_id <> related_course_id
    )
);

CREATE INDEX IF NOT EXISTS idx_recommendation_tracking_course
    ON recommendation_tracking_events(course_id, event_type, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_recommendation_tracking_pair
    ON recommendation_tracking_events(course_id, related_course_id, event_type, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_recommendation_tracking_student
    ON recommendation_tracking_events(student_id, event_type, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_recommendation_tracking_enrollment
    ON recommendation_tracking_events(student_id, course_id, related_course_id, occurred_at DESC)
    WHERE event_type = 'ENROLLMENT' AND student_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS course_pair_stats (
    id UUID PRIMARY KEY,
    course_id UUID NOT NULL,
    related_course_id UUID NOT NULL,
    support_count INT NOT NULL DEFAULT 0,
    impression_count INT NOT NULL DEFAULT 0,
    click_count INT NOT NULL DEFAULT 0,
    enroll_count INT NOT NULL DEFAULT 0,
    score NUMERIC(6,3) NOT NULL DEFAULT 0,
    model_version VARCHAR(80) NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_course_pair_stats_not_self CHECK (course_id <> related_course_id),
    CONSTRAINT ux_course_pair_stats_pair UNIQUE (course_id, related_course_id)
);

CREATE INDEX IF NOT EXISTS idx_course_pair_stats_course
    ON course_pair_stats(course_id, score DESC);
