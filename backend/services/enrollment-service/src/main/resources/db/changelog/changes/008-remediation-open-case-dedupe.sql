-- liquibase formatted sql
-- changeset courseflow:enrollment-008-remediation-open-case-dedupe

CREATE UNIQUE INDEX IF NOT EXISTS uk_enrollment_remediation_open_promotion
    ON enrollment_remediation_cases (promotion_application_id)
    WHERE promotion_application_id IS NOT NULL
      AND status IN ('OPEN', 'IN_PROGRESS');

CREATE UNIQUE INDEX IF NOT EXISTS uk_enrollment_remediation_open_order
    ON enrollment_remediation_cases (order_id)
    WHERE order_id IS NOT NULL
      AND status IN ('OPEN', 'IN_PROGRESS');
