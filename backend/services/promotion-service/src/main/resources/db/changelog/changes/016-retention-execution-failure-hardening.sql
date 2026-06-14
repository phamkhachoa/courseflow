-- liquibase formatted sql

-- changeset courseflow:promotion-016-retention-approval-execution-failed
ALTER TABLE incentive_retention_approvals
    ADD COLUMN IF NOT EXISTS failed_at TIMESTAMPTZ;

ALTER TABLE incentive_retention_approvals
    DROP CONSTRAINT IF EXISTS chk_incentive_retention_approval_status;

ALTER TABLE incentive_retention_approvals
    ADD CONSTRAINT chk_incentive_retention_approval_status
        CHECK (status IN (
            'PENDING_APPROVAL',
            'APPROVED',
            'REJECTED',
            'EXECUTED',
            'EXECUTION_FAILED'
        ));

-- changeset courseflow:promotion-016-retention-active-approval-unique
CREATE UNIQUE INDEX IF NOT EXISTS uq_incentive_retention_active_approval_dry_run
    ON incentive_retention_approvals (
        policy_id,
        scope_key,
        dry_run_id,
        dry_run_result_hash,
        batch_limit
    )
    WHERE status IN ('PENDING_APPROVAL', 'APPROVED');
