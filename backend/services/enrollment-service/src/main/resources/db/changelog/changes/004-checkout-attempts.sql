-- liquibase formatted sql
-- changeset courseflow:enrollment-004-checkout-attempts

CREATE TABLE IF NOT EXISTS enrollment_checkout_attempts (
    id UUID PRIMARY KEY,
    idempotency_key VARCHAR(180) NOT NULL,
    request_hash VARCHAR(96) NOT NULL,
    course_id UUID NOT NULL,
    student_id VARCHAR(64) NOT NULL,
    promotion_preview_id VARCHAR(120),
    reservation_id UUID,
    redemption_id UUID,
    enrollment_id UUID,
    status VARCHAR(40) NOT NULL,
    retry_count INT NOT NULL DEFAULT 0,
    next_retry_at TIMESTAMPTZ,
    response_json JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT uk_enrollment_checkout_attempt_idempotency_key UNIQUE (idempotency_key),
    CONSTRAINT chk_enrollment_checkout_attempt_status CHECK (
        status IN ('STARTED', 'RESERVED', 'ENROLLMENT_CREATED', 'COMMITTING', 'SUCCEEDED',
                   'COMMIT_FAILED', 'MANUAL_REVIEW', 'CANCELLED', 'FAILED')
    )
);

CREATE INDEX IF NOT EXISTS idx_enrollment_checkout_attempts_scope
    ON enrollment_checkout_attempts (course_id, student_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_enrollment_checkout_attempts_status
    ON enrollment_checkout_attempts (status, updated_at DESC);
