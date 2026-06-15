-- liquibase formatted sql

-- changeset courseflow:gradebook-002-assessment-ops-audit
CREATE TABLE IF NOT EXISTS gradebook_audit_logs (
    id UUID PRIMARY KEY,
    action VARCHAR(80) NOT NULL,
    course_id UUID NOT NULL,
    student_id VARCHAR(64),
    grade_item_id UUID,
    grade_entry_id UUID,
    final_grade_id UUID,
    actor_id VARCHAR(64) NOT NULL,
    reason_codes JSONB NOT NULL DEFAULT '[]'::jsonb,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gradebook_audit_course_created
    ON gradebook_audit_logs (course_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_gradebook_audit_student_created
    ON gradebook_audit_logs (student_id, created_at DESC);
