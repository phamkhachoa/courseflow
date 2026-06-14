-- liquibase formatted sql

-- changeset courseflow:promotion-019-operation-approvals
CREATE TABLE IF NOT EXISTS incentive_operation_approvals (
    id UUID PRIMARY KEY,
    operation_type VARCHAR(80) NOT NULL,
    target_type VARCHAR(80) NOT NULL,
    target_id UUID NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'PENDING_APPROVAL',
    tenant_id VARCHAR(80) NOT NULL,
    application_id VARCHAR(80) NOT NULL,
    campaign_id UUID,
    scope_key VARCHAR(220) NOT NULL,
    request_hash VARCHAR(160) NOT NULL,
    result_hash VARCHAR(160) NOT NULL,
    subject_hash VARCHAR(160) NOT NULL,
    requested_rows INTEGER NOT NULL,
    valid_rows INTEGER NOT NULL,
    invalid_rows INTEGER NOT NULL,
    duplicate_in_file_rows INTEGER NOT NULL,
    duplicate_existing_rows INTEGER NOT NULL,
    storage_inventory_ready BOOLEAN NOT NULL DEFAULT FALSE,
    commit_ready BOOLEAN NOT NULL DEFAULT FALSE,
    subject_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    reason TEXT NOT NULL,
    change_ticket VARCHAR(160) NOT NULL,
    note TEXT,
    requested_by VARCHAR(160) NOT NULL,
    approved_by VARCHAR(160),
    rejected_by VARCHAR(160),
    executed_by VARCHAR(160),
    correlation_id VARCHAR(160) NOT NULL,
    source_client_id VARCHAR(160),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMPTZ,
    rejected_at TIMESTAMPTZ,
    executed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL,
    version BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT chk_operation_approval_status CHECK (
        status IN ('PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'EXECUTED')
    ),
    CONSTRAINT chk_operation_approval_type CHECK (
        operation_type IN ('COUPON_IMPORT_COMMIT')
        AND target_type IN ('COUPON_IMPORT_DRY_RUN')
    ),
    CONSTRAINT chk_operation_approval_counts CHECK (
        requested_rows >= 0
        AND valid_rows >= 0
        AND invalid_rows >= 0
        AND duplicate_in_file_rows >= 0
        AND duplicate_existing_rows >= 0
    ),
    CONSTRAINT chk_operation_approval_expiry CHECK (expires_at > created_at)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_operation_approval_active_subject
    ON incentive_operation_approvals (operation_type, target_type, target_id, subject_hash)
    WHERE status IN ('PENDING_APPROVAL', 'APPROVED');

CREATE INDEX IF NOT EXISTS idx_operation_approval_queue
    ON incentive_operation_approvals (tenant_id, application_id, campaign_id, status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_operation_approval_target
    ON incentive_operation_approvals (operation_type, target_type, target_id, created_at DESC);

-- changeset courseflow:promotion-019-coupon-import-operation-approval-link
ALTER TABLE incentive_coupon_import_operations
    ADD COLUMN IF NOT EXISTS approval_id UUID REFERENCES incentive_operation_approvals(id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_coupon_import_operation_approval
    ON incentive_coupon_import_operations (approval_id)
    WHERE approval_id IS NOT NULL;
