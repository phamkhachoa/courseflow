-- liquibase formatted sql
-- changeset courseflow:enrollment-009-remediation-ops-filter-indexes

CREATE INDEX IF NOT EXISTS idx_enrollment_remediation_cases_enrollment
    ON enrollment_remediation_cases (enrollment_id)
    WHERE enrollment_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_enrollment_remediation_cases_assignee_queue
    ON enrollment_remediation_cases (assignee_id, status, sla_due_at, created_at);

CREATE INDEX IF NOT EXISTS idx_enrollment_promotion_applications_coupon
    ON enrollment_promotion_applications (coupon_id)
    WHERE coupon_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_enrollment_promotion_applications_redemption
    ON enrollment_promotion_applications (redemption_id)
    WHERE redemption_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_enrollment_remediation_actions_payload
    ON enrollment_remediation_case_actions USING GIN (payload_json);
