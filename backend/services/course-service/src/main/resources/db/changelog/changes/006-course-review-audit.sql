-- liquibase formatted sql
-- Append-only review workflow history for enterprise content operations.

-- changeset courseflow:course-006-course-review-audit
CREATE TABLE IF NOT EXISTS course_review_audit_log (
    id UUID PRIMARY KEY,
    course_id UUID NOT NULL REFERENCES courses(id),
    version_no INT NOT NULL,
    actor_id VARCHAR(64) NOT NULL,
    actor_role VARCHAR(120),
    action VARCHAR(60) NOT NULL,
    from_state VARCHAR(40),
    to_state VARCHAR(40),
    note TEXT,
    checklist JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_course_review_audit_course_created
    ON course_review_audit_log(course_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_course_review_audit_action_created
    ON course_review_audit_log(action, created_at DESC);
