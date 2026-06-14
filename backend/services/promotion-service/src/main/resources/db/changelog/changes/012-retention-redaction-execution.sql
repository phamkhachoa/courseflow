-- liquibase formatted sql

-- changeset courseflow:promotion-012-retention-redaction-operation
CREATE TABLE IF NOT EXISTS incentive_retention_operations (
    id UUID PRIMARY KEY,
    policy_id VARCHAR(120) NOT NULL,
    policy_version VARCHAR(40) NOT NULL,
    target_dataset VARCHAR(120) NOT NULL,
    tenant_id VARCHAR(80),
    application_id VARCHAR(80),
    dry_run_id UUID NOT NULL,
    dry_run_result_hash VARCHAR(128) NOT NULL,
    cutoff_at TIMESTAMPTZ NOT NULL,
    expected_eligible_count BIGINT NOT NULL,
    batch_limit INTEGER NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'IN_PROGRESS',
    idempotency_key VARCHAR(160) NOT NULL,
    request_hash VARCHAR(128) NOT NULL,
    reason TEXT NOT NULL,
    change_ticket VARCHAR(160) NOT NULL,
    restore_drill_ref VARCHAR(255) NOT NULL,
    approved_by VARCHAR(160),
    executed_by VARCHAR(160),
    correlation_id VARCHAR(160) NOT NULL,
    rows_redacted BIGINT NOT NULL DEFAULT 0,
    last_error TEXT,
    response_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    CONSTRAINT uq_incentive_retention_operation_idempotency
        UNIQUE (policy_id, idempotency_key),
    CONSTRAINT chk_incentive_retention_operation_status
        CHECK (status IN ('IN_PROGRESS', 'SUCCEEDED', 'FAILED')),
    CONSTRAINT chk_incentive_retention_operation_scope
        CHECK ((tenant_id IS NULL AND application_id IS NULL)
            OR (tenant_id IS NOT NULL AND application_id IS NOT NULL)),
    CONSTRAINT chk_incentive_retention_operation_batch_limit
        CHECK (batch_limit > 0),
    CONSTRAINT chk_incentive_retention_operation_counts
        CHECK (expected_eligible_count >= 0 AND rows_redacted >= 0)
);

CREATE INDEX IF NOT EXISTS idx_incentive_retention_operations_status
    ON incentive_retention_operations (status, created_at);

CREATE INDEX IF NOT EXISTS idx_incentive_retention_operations_scope
    ON incentive_retention_operations (tenant_id, application_id, created_at);

CREATE INDEX IF NOT EXISTS idx_incentive_reservations_legacy_snapshot_redaction
    ON incentive_reservations (
        tenant_id,
        application_id,
        coalesce(cancelled_at, expires_at),
        id
    )
    WHERE status IN ('EXPIRED', 'CANCELLED')
      AND request_json <> '{}'::jsonb
      AND coalesce(request_json ->> 'requestSnapshotMinimized', 'false') <> 'true'
      AND coalesce(request_json ->> 'retentionRedacted', 'false') <> 'true';
