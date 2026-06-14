-- liquibase formatted sql
-- Promotion commit remediation needs its own retry clock; checkout attempts are only the learner-facing trace.

-- changeset courseflow:enrollment-005-promotion-application-retry-schedule
ALTER TABLE enrollment_promotion_applications
    ADD COLUMN IF NOT EXISTS retry_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS next_retry_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS last_retry_error TEXT;

UPDATE enrollment_promotion_applications
SET next_retry_at = COALESCE(next_retry_at, updated_at)
WHERE status = 'COMMIT_FAILED'
  AND next_retry_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_enrollment_promotion_applications_retry_due
    ON enrollment_promotion_applications (status, next_retry_at, updated_at)
    WHERE status = 'COMMIT_FAILED';
