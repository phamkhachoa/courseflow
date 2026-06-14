-- liquibase formatted sql

-- changeset courseflow:promotion-018-coupon-import-batch-outcome
ALTER TABLE incentive_coupon_import_batches
    ADD COLUMN IF NOT EXISTS committed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS committed_by VARCHAR(80),
    ADD COLUMN IF NOT EXISTS committed_operation_id UUID,
    ADD COLUMN IF NOT EXISTS committed_rows INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS failure_reason VARCHAR(255);

ALTER TABLE incentive_coupon_import_batches
    DROP CONSTRAINT IF EXISTS chk_coupon_import_batch_committed_rows;

ALTER TABLE incentive_coupon_import_batches
    ADD CONSTRAINT chk_coupon_import_batch_committed_rows CHECK (committed_rows >= 0);

-- changeset courseflow:promotion-018-coupon-import-operations
CREATE TABLE IF NOT EXISTS incentive_coupon_import_operations (
    id UUID PRIMARY KEY,
    dry_run_id UUID NOT NULL REFERENCES incentive_coupon_import_batches(id),
    tenant_id VARCHAR(80) NOT NULL,
    application_id VARCHAR(80) NOT NULL,
    campaign_id UUID NOT NULL REFERENCES incentive_campaigns(id),
    result_hash VARCHAR(160) NOT NULL,
    request_hash VARCHAR(160) NOT NULL,
    idempotency_key_hash VARCHAR(160) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'SUCCEEDED',
    requested_rows INTEGER NOT NULL,
    imported_rows INTEGER NOT NULL,
    reason VARCHAR(500) NOT NULL,
    change_ticket VARCHAR(160) NOT NULL,
    response_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by VARCHAR(80),
    correlation_id VARCHAR(120),
    source_client_id VARCHAR(160),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT uk_coupon_import_operation_dry_run UNIQUE (dry_run_id),
    CONSTRAINT chk_coupon_import_operation_status CHECK (status IN ('SUCCEEDED')),
    CONSTRAINT chk_coupon_import_operation_counts CHECK (requested_rows >= 0 AND imported_rows >= 0)
);

CREATE INDEX IF NOT EXISTS idx_coupon_import_operation_campaign_time
    ON incentive_coupon_import_operations (campaign_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_coupon_import_operation_idempotency_hash
    ON incentive_coupon_import_operations (tenant_id, application_id, idempotency_key_hash);

CREATE INDEX IF NOT EXISTS idx_coupon_import_batch_expired_uncommitted
    ON incentive_coupon_import_batches (expires_at)
    WHERE expires_at IS NOT NULL AND committed_at IS NULL;
