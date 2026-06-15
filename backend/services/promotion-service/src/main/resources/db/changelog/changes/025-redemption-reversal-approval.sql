-- liquibase formatted sql

-- changeset courseflow:promotion-025-redemption-reversal-approval
ALTER TABLE incentive_operation_approvals
    DROP CONSTRAINT IF EXISTS chk_operation_approval_type;

ALTER TABLE incentive_operation_approvals
    ADD CONSTRAINT chk_operation_approval_type CHECK (
        (
            operation_type = 'COUPON_IMPORT_COMMIT'
            AND target_type = 'COUPON_IMPORT_DRY_RUN'
        )
        OR (
            operation_type = 'PROMOTION_REDEMPTION_REVERSE'
            AND target_type = 'PROMOTION_REDEMPTION'
        )
    );

CREATE INDEX IF NOT EXISTS idx_operation_approval_operation_queue
    ON incentive_operation_approvals (operation_type, tenant_id, application_id, campaign_id, status, created_at DESC);
