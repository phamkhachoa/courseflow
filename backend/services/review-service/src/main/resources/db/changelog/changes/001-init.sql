-- liquibase formatted sql
-- Single consolidated baseline for review-service. Merged from the previous
-- 001/002/.../900 changeset files (pre-production cleanup).

-- ============================================================
-- merged from 001-init.sql
-- ============================================================
-- changeset courseflow:review-001-init
CREATE TABLE IF NOT EXISTS course_reviews (
    id UUID PRIMARY KEY,
    course_id UUID NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    rating SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    title VARCHAR(255),
    body TEXT,
    status VARCHAR(40) NOT NULL DEFAULT 'PUBLISHED', -- PUBLISHED, HIDDEN, FLAGGED
    helpful_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version BIGINT NOT NULL DEFAULT 0,
    UNIQUE (course_id, user_id)
);

CREATE TABLE IF NOT EXISTS review_helpful_votes (
    id UUID PRIMARY KEY,
    review_id UUID NOT NULL REFERENCES course_reviews(id),
    user_id VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (review_id, user_id)
);

-- Maintained aggregate read model per course (avg + count + star histogram).
CREATE TABLE IF NOT EXISTS course_rating_summary (
    course_id UUID PRIMARY KEY,
    review_count INT NOT NULL DEFAULT 0,
    average_rating NUMERIC(3,2) NOT NULL DEFAULT 0,
    count_1 INT NOT NULL DEFAULT 0,
    count_2 INT NOT NULL DEFAULT 0,
    count_3 INT NOT NULL DEFAULT 0,
    count_4 INT NOT NULL DEFAULT 0,
    count_5 INT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version BIGINT NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_course_reviews_course ON course_reviews(course_id);

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
-- changeset courseflow:review-900-demo context=demo
INSERT INTO course_reviews (id, course_id, user_id, rating, title, body)
VALUES (
    '6f1e0a00-0000-4000-8000-000000000001',
    '11111111-1111-4111-8111-111111111111',
    'student-1',
    5,
    'Excellent course',
    'Clear explanations and great hands-on labs.'
) ON CONFLICT (course_id, user_id) DO NOTHING;

INSERT INTO course_rating_summary (course_id, review_count, average_rating, count_5)
VALUES ('11111111-1111-4111-8111-111111111111', 1, 5.00, 1)
ON CONFLICT (course_id) DO NOTHING;
