-- liquibase formatted sql
-- changeset courseflow:loyalty-003-ledger-operations

CREATE TABLE IF NOT EXISTS loyalty_point_lots (
    id UUID PRIMARY KEY,
    program_uuid UUID NOT NULL REFERENCES loyalty_programs(id),
    account_id UUID NOT NULL REFERENCES loyalty_accounts(id),
    source_entry_id UUID NOT NULL REFERENCES loyalty_points_entries(id),
    tenant_id VARCHAR(80) NOT NULL,
    application_id VARCHAR(80) NOT NULL,
    program_id VARCHAR(120) NOT NULL,
    profile_id VARCHAR(160) NOT NULL,
    entry_type VARCHAR(40) NOT NULL,
    original_points BIGINT NOT NULL,
    consumed_points BIGINT NOT NULL DEFAULT 0,
    remaining_points BIGINT NOT NULL,
    source_reference VARCHAR(180) NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT uk_loyalty_point_lot_source UNIQUE (source_entry_id),
    CONSTRAINT chk_loyalty_point_lot_points CHECK (
        original_points > 0
        AND consumed_points >= 0
        AND remaining_points >= 0
        AND consumed_points + remaining_points = original_points
    )
);
CREATE INDEX IF NOT EXISTS idx_loyalty_point_lots_account
    ON loyalty_point_lots (account_id, expires_at, occurred_at);
CREATE INDEX IF NOT EXISTS idx_loyalty_point_lots_expiry
    ON loyalty_point_lots (program_uuid, expires_at, remaining_points)
    WHERE expires_at IS NOT NULL AND remaining_points > 0;

CREATE TABLE IF NOT EXISTS loyalty_adjustment_approvals (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(80) NOT NULL,
    application_id VARCHAR(80) NOT NULL,
    program_id VARCHAR(120) NOT NULL,
    profile_id VARCHAR(160) NOT NULL,
    points_delta BIGINT NOT NULL,
    source_reference VARCHAR(180) NOT NULL,
    idempotency_key VARCHAR(180) NOT NULL,
    reason TEXT NOT NULL,
    correlation_id VARCHAR(160) NOT NULL,
    occurred_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    request_hash VARCHAR(128) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'PENDING',
    requested_by VARCHAR(160) NOT NULL,
    reviewed_by VARCHAR(160),
    review_note TEXT,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ,
    executed_at TIMESTAMPTZ,
    executed_entry_id UUID REFERENCES loyalty_points_entries(id),
    version BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT chk_loyalty_adjustment_approval_status CHECK (
        status IN ('PENDING', 'APPROVED', 'REJECTED', 'EXECUTED')
    ),
    CONSTRAINT chk_loyalty_adjustment_approval_delta CHECK (points_delta <> 0)
);
CREATE INDEX IF NOT EXISTS idx_loyalty_adjustment_approvals_scope
    ON loyalty_adjustment_approvals (tenant_id, application_id, status, requested_at DESC);
CREATE INDEX IF NOT EXISTS idx_loyalty_adjustment_approvals_profile
    ON loyalty_adjustment_approvals (tenant_id, application_id, program_id, profile_id, requested_at DESC);
