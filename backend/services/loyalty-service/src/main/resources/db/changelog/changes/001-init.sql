-- liquibase formatted sql
-- Generic loyalty bounded context baseline. The schema intentionally avoids LMS-specific fields.

-- changeset courseflow:loyalty-001-init
CREATE TABLE IF NOT EXISTS loyalty_programs (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(80) NOT NULL,
    application_id VARCHAR(80) NOT NULL,
    program_id VARCHAR(120) NOT NULL,
    name VARCHAR(255) NOT NULL,
    point_unit VARCHAR(40) NOT NULL DEFAULT 'POINT',
    status VARCHAR(40) NOT NULL DEFAULT 'ACTIVE',
    allow_negative_balance BOOLEAN NOT NULL DEFAULT FALSE,
    default_points_expiry_days INTEGER,
    created_by VARCHAR(160),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT uk_loyalty_program_scope UNIQUE (tenant_id, application_id, program_id),
    CONSTRAINT chk_loyalty_program_status CHECK (status IN ('DRAFT', 'ACTIVE', 'SUSPENDED', 'ARCHIVED')),
    CONSTRAINT chk_loyalty_program_expiry CHECK (default_points_expiry_days IS NULL OR default_points_expiry_days > 0)
);
CREATE INDEX IF NOT EXISTS idx_loyalty_program_scope_status
    ON loyalty_programs (tenant_id, application_id, status);

CREATE TABLE IF NOT EXISTS loyalty_accounts (
    id UUID PRIMARY KEY,
    program_uuid UUID NOT NULL REFERENCES loyalty_programs(id),
    tenant_id VARCHAR(80) NOT NULL,
    application_id VARCHAR(80) NOT NULL,
    program_id VARCHAR(120) NOT NULL,
    profile_id VARCHAR(160) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'ACTIVE',
    opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    version BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT uk_loyalty_account_profile UNIQUE (tenant_id, application_id, program_id, profile_id),
    CONSTRAINT chk_loyalty_account_status CHECK (status IN ('ACTIVE', 'SUSPENDED', 'CLOSED'))
);
CREATE INDEX IF NOT EXISTS idx_loyalty_accounts_program
    ON loyalty_accounts (program_uuid, status);

CREATE TABLE IF NOT EXISTS loyalty_points_entries (
    id UUID PRIMARY KEY,
    program_uuid UUID NOT NULL REFERENCES loyalty_programs(id),
    account_id UUID NOT NULL REFERENCES loyalty_accounts(id),
    tenant_id VARCHAR(80) NOT NULL,
    application_id VARCHAR(80) NOT NULL,
    program_id VARCHAR(120) NOT NULL,
    profile_id VARCHAR(160) NOT NULL,
    entry_type VARCHAR(40) NOT NULL,
    points_delta BIGINT NOT NULL,
    source_reference VARCHAR(180) NOT NULL,
    source_request_hash VARCHAR(128) NOT NULL,
    reversal_of_entry_id UUID REFERENCES loyalty_points_entries(id),
    reason TEXT,
    correlation_id VARCHAR(160),
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_loyalty_points_entry_type CHECK (entry_type IN ('EARN', 'BURN', 'EXPIRE', 'REVERSE', 'ADJUST')),
    CONSTRAINT chk_loyalty_points_delta CHECK (points_delta <> 0)
);
CREATE UNIQUE INDEX IF NOT EXISTS uk_loyalty_points_source
    ON loyalty_points_entries (program_uuid, entry_type, source_reference)
    WHERE reversal_of_entry_id IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uk_loyalty_points_reversal
    ON loyalty_points_entries (reversal_of_entry_id)
    WHERE reversal_of_entry_id IS NOT NULL AND entry_type = 'REVERSE';
CREATE INDEX IF NOT EXISTS idx_loyalty_points_account_time
    ON loyalty_points_entries (account_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_loyalty_points_expiry
    ON loyalty_points_entries (program_uuid, expires_at)
    WHERE expires_at IS NOT NULL AND points_delta > 0;

CREATE TABLE IF NOT EXISTS loyalty_idempotency_keys (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(80) NOT NULL,
    application_id VARCHAR(80) NOT NULL,
    operation VARCHAR(40) NOT NULL,
    idempotency_key VARCHAR(180) NOT NULL,
    request_hash VARCHAR(128) NOT NULL,
    response_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(40) NOT NULL DEFAULT 'SUCCEEDED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT uk_loyalty_idempotency_key UNIQUE (tenant_id, application_id, operation, idempotency_key),
    CONSTRAINT chk_loyalty_idempotency_status CHECK (status IN ('IN_PROGRESS', 'SUCCEEDED', 'FAILED'))
);
CREATE INDEX IF NOT EXISTS idx_loyalty_idempotency_expiry
    ON loyalty_idempotency_keys (expires_at);

CREATE TABLE IF NOT EXISTS loyalty_audit_events (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(80),
    application_id VARCHAR(80),
    aggregate_id VARCHAR(160) NOT NULL,
    aggregate_type VARCHAR(80) NOT NULL,
    action VARCHAR(80) NOT NULL,
    actor_id VARCHAR(160),
    note TEXT,
    correlation_id VARCHAR(160),
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_loyalty_audit_aggregate
    ON loyalty_audit_events (aggregate_type, aggregate_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_loyalty_audit_scope_time
    ON loyalty_audit_events (tenant_id, application_id, created_at DESC);

CREATE TABLE IF NOT EXISTS outbox_events (
    id UUID PRIMARY KEY,
    aggregate_id VARCHAR(255) NOT NULL,
    aggregate_type VARCHAR(120) NOT NULL,
    event_type VARCHAR(120) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_outbox_unpublished
    ON outbox_events (created_at, id)
    WHERE published_at IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uk_outbox_loyalty_points_event
    ON outbox_events (aggregate_id, event_type)
    WHERE aggregate_type = 'loyalty-points-entry';
