-- liquibase formatted sql
-- changeset courseflow:enrollment-002-promotion-applications

CREATE TABLE IF NOT EXISTS enrollment_promotion_applications (
    id UUID PRIMARY KEY,
    enrollment_id UUID NOT NULL REFERENCES enrollments(id),
    student_id VARCHAR(64) NOT NULL,
    course_id UUID NOT NULL,
    status VARCHAR(40) NOT NULL,
    coupon_code VARCHAR(120),
    coupon_id UUID,
    reservation_id UUID,
    redemption_id UUID,
    idempotency_key VARCHAR(180),
    reason_codes_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    effects_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT uk_enrollment_promotion_application_enrollment UNIQUE (enrollment_id),
    CONSTRAINT chk_enrollment_promotion_application_status CHECK (
        status IN ('RESERVED', 'APPLIED', 'COMMIT_FAILED', 'SKIPPED', 'UNAVAILABLE', 'REVERSED', 'CANCELLED', 'MANUAL_REVIEW')
    )
);

CREATE INDEX IF NOT EXISTS idx_enrollment_promotion_applications_scope
    ON enrollment_promotion_applications (course_id, student_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_enrollment_promotion_applications_status
    ON enrollment_promotion_applications (status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_enrollment_promotion_applications_reservation
    ON enrollment_promotion_applications (reservation_id)
    WHERE reservation_id IS NOT NULL;
