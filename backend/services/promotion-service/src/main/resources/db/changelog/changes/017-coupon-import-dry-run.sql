-- liquibase formatted sql

-- changeset courseflow:promotion-017-coupon-import-dry-run-batch
CREATE TABLE IF NOT EXISTS incentive_coupon_import_batches (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(80) NOT NULL,
    application_id VARCHAR(80) NOT NULL,
    campaign_id UUID NOT NULL REFERENCES incentive_campaigns(id),
    request_hash VARCHAR(160) NOT NULL,
    idempotency_key VARCHAR(160),
    mode VARCHAR(40) NOT NULL DEFAULT 'DRY_RUN',
    status VARCHAR(40) NOT NULL DEFAULT 'COMPLETED',
    content_hash VARCHAR(160) NOT NULL,
    result_hash VARCHAR(160) NOT NULL,
    requested_rows INTEGER NOT NULL,
    valid_rows INTEGER NOT NULL,
    invalid_rows INTEGER NOT NULL,
    duplicate_in_file_rows INTEGER NOT NULL,
    duplicate_existing_rows INTEGER NOT NULL,
    storage_inventory_ready BOOLEAN NOT NULL DEFAULT FALSE,
    commit_ready BOOLEAN NOT NULL DEFAULT FALSE,
    result_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by VARCHAR(80),
    correlation_id VARCHAR(120),
    source_client_id VARCHAR(160),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    version BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT chk_coupon_import_batch_mode CHECK (mode IN ('DRY_RUN')),
    CONSTRAINT chk_coupon_import_batch_status CHECK (status IN ('COMPLETED')),
    CONSTRAINT chk_coupon_import_batch_counts CHECK (
        requested_rows >= 0
        AND valid_rows >= 0
        AND invalid_rows >= 0
        AND duplicate_in_file_rows >= 0
        AND duplicate_existing_rows >= 0
    )
);

CREATE INDEX IF NOT EXISTS idx_coupon_import_batch_campaign_time
    ON incentive_coupon_import_batches (campaign_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_coupon_import_batch_request_hash
    ON incentive_coupon_import_batches (campaign_id, request_hash, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_coupon_import_batch_idempotency
    ON incentive_coupon_import_batches (campaign_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_coupon_import_batch_tenant_app_time
    ON incentive_coupon_import_batches (tenant_id, application_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_coupon_import_batch_expires_at
    ON incentive_coupon_import_batches (expires_at)
    WHERE expires_at IS NOT NULL;

-- changeset courseflow:promotion-017-coupon-import-dry-run-rows
CREATE TABLE IF NOT EXISTS incentive_coupon_import_rows (
    id UUID PRIMARY KEY,
    batch_id UUID NOT NULL REFERENCES incentive_coupon_import_batches(id) ON DELETE CASCADE,
    row_number INTEGER NOT NULL,
    code_mask VARCHAR(80),
    row_status VARCHAR(40) NOT NULL,
    issue_codes_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    issues_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_coupon_import_row_number UNIQUE (batch_id, row_number),
    CONSTRAINT chk_coupon_import_row_status CHECK (row_status IN ('VALID', 'INVALID'))
);

CREATE INDEX IF NOT EXISTS idx_coupon_import_rows_batch_status
    ON incentive_coupon_import_rows (batch_id, row_status, row_number);
