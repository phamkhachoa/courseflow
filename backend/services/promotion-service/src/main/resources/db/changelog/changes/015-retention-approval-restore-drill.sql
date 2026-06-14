-- liquibase formatted sql

-- changeset courseflow:promotion-015-retention-restore-drill
CREATE TABLE IF NOT EXISTS incentive_restore_drills (
    id UUID PRIMARY KEY,
    restore_drill_ref VARCHAR(160) NOT NULL,
    database_name VARCHAR(120) NOT NULL,
    backup_path VARCHAR(500) NOT NULL,
    artifact_hash VARCHAR(128) NOT NULL,
    status VARCHAR(40) NOT NULL,
    checked_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_by VARCHAR(160) NOT NULL,
    note TEXT,
    correlation_id VARCHAR(160) NOT NULL,
    source_client_id VARCHAR(160),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_incentive_restore_drill_ref UNIQUE (restore_drill_ref),
    CONSTRAINT chk_incentive_restore_drill_status CHECK (status IN ('PASSED', 'FAILED')),
    CONSTRAINT chk_incentive_restore_drill_time CHECK (checked_at < expires_at)
);

CREATE INDEX IF NOT EXISTS idx_incentive_restore_drill_status
    ON incentive_restore_drills (database_name, status, expires_at);

-- changeset courseflow:promotion-015-retention-approval
CREATE TABLE IF NOT EXISTS incentive_retention_approvals (
    id UUID PRIMARY KEY,
    status VARCHAR(40) NOT NULL DEFAULT 'PENDING_APPROVAL',
    policy_id VARCHAR(120) NOT NULL,
    policy_version VARCHAR(40) NOT NULL,
    target_dataset VARCHAR(120) NOT NULL,
    scope_key VARCHAR(180) NOT NULL,
    tenant_id VARCHAR(80),
    application_id VARCHAR(80),
    as_of TIMESTAMPTZ NOT NULL,
    cutoff_at TIMESTAMPTZ NOT NULL,
    retention_days INTEGER NOT NULL,
    dry_run_id UUID NOT NULL,
    dry_run_result_hash VARCHAR(128) NOT NULL,
    eligible_count BIGINT NOT NULL,
    batch_limit INTEGER NOT NULL,
    reason TEXT NOT NULL,
    change_ticket VARCHAR(160) NOT NULL,
    restore_drill_ref VARCHAR(160) NOT NULL REFERENCES incentive_restore_drills(restore_drill_ref),
    requested_by VARCHAR(160) NOT NULL,
    approved_by VARCHAR(160),
    rejected_by VARCHAR(160),
    executed_by VARCHAR(160),
    note TEXT,
    correlation_id VARCHAR(160) NOT NULL,
    source_client_id VARCHAR(160),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMPTZ,
    rejected_at TIMESTAMPTZ,
    executed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT chk_incentive_retention_approval_status
        CHECK (status IN ('PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'EXECUTED')),
    CONSTRAINT chk_incentive_retention_approval_scope
        CHECK ((tenant_id IS NULL AND application_id IS NULL)
            OR (tenant_id IS NOT NULL AND application_id IS NOT NULL)),
    CONSTRAINT chk_incentive_retention_approval_batch_limit CHECK (batch_limit > 0),
    CONSTRAINT chk_incentive_retention_approval_counts CHECK (eligible_count >= 0),
    CONSTRAINT chk_incentive_retention_approval_ttl CHECK (as_of < expires_at)
);

CREATE INDEX IF NOT EXISTS idx_incentive_retention_approvals_scope_status
    ON incentive_retention_approvals (policy_id, scope_key, status, created_at);

CREATE INDEX IF NOT EXISTS idx_incentive_retention_approvals_dry_run
    ON incentive_retention_approvals (dry_run_id, dry_run_result_hash);

ALTER TABLE incentive_retention_operations
    ADD COLUMN IF NOT EXISTS approval_id UUID REFERENCES incentive_retention_approvals(id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_incentive_retention_operation_approval
    ON incentive_retention_operations (approval_id)
    WHERE approval_id IS NOT NULL;
