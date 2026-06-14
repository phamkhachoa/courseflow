-- liquibase formatted sql
-- changeset courseflow:enrollment-003-promotion-application-reversed-status

ALTER TABLE enrollment_promotion_applications
    DROP CONSTRAINT IF EXISTS chk_enrollment_promotion_application_status;

ALTER TABLE enrollment_promotion_applications
    ADD CONSTRAINT chk_enrollment_promotion_application_status CHECK (
        status IN ('RESERVED', 'APPLIED', 'COMMIT_FAILED', 'SKIPPED', 'UNAVAILABLE', 'REVERSED', 'CANCELLED', 'MANUAL_REVIEW')
    );
