-- liquibase formatted sql
-- changeset courseflow:loyalty-005-rewards

CREATE TABLE IF NOT EXISTS loyalty_rewards (
    id UUID PRIMARY KEY,
    program_uuid UUID NOT NULL REFERENCES loyalty_programs(id),
    tenant_id VARCHAR(80) NOT NULL,
    application_id VARCHAR(80) NOT NULL,
    program_id VARCHAR(120) NOT NULL,
    reward_code VARCHAR(120) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    points_cost BIGINT NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'DRAFT',
    starts_at TIMESTAMPTZ,
    ends_at TIMESTAMPTZ,
    inventory_limit BIGINT,
    per_profile_limit INTEGER,
    fulfillment_type VARCHAR(60) NOT NULL DEFAULT 'MANUAL',
    fulfillment_config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by VARCHAR(160),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT uk_loyalty_reward_code UNIQUE (tenant_id, application_id, program_id, reward_code),
    CONSTRAINT chk_loyalty_reward_points CHECK (points_cost > 0),
    CONSTRAINT chk_loyalty_reward_status CHECK (status IN ('DRAFT', 'ACTIVE', 'SUSPENDED', 'ARCHIVED')),
    CONSTRAINT chk_loyalty_reward_inventory CHECK (inventory_limit IS NULL OR inventory_limit > 0),
    CONSTRAINT chk_loyalty_reward_profile_limit CHECK (per_profile_limit IS NULL OR per_profile_limit > 0),
    CONSTRAINT chk_loyalty_reward_window CHECK (ends_at IS NULL OR starts_at IS NULL OR ends_at > starts_at)
);
CREATE INDEX IF NOT EXISTS idx_loyalty_rewards_scope_status
    ON loyalty_rewards (tenant_id, application_id, program_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_loyalty_rewards_active_window
    ON loyalty_rewards (program_uuid, status, starts_at, ends_at);

CREATE TABLE IF NOT EXISTS loyalty_reward_redemptions (
    id UUID PRIMARY KEY,
    reward_id UUID NOT NULL REFERENCES loyalty_rewards(id),
    program_uuid UUID NOT NULL REFERENCES loyalty_programs(id),
    account_id UUID NOT NULL REFERENCES loyalty_accounts(id),
    burn_entry_id UUID NOT NULL REFERENCES loyalty_points_entries(id),
    reversal_entry_id UUID REFERENCES loyalty_points_entries(id),
    tenant_id VARCHAR(80) NOT NULL,
    application_id VARCHAR(80) NOT NULL,
    program_id VARCHAR(120) NOT NULL,
    profile_id VARCHAR(160) NOT NULL,
    reward_code VARCHAR(120) NOT NULL,
    points_cost BIGINT NOT NULL,
    source_reference VARCHAR(180) NOT NULL,
    idempotency_key VARCHAR(180) NOT NULL,
    request_hash VARCHAR(128) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'COMMITTED',
    fulfillment_status VARCHAR(40) NOT NULL DEFAULT 'PENDING',
    fulfillment_ref VARCHAR(180),
    fulfillment_note TEXT,
    reward_snapshot_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    correlation_id VARCHAR(160),
    note TEXT,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    redeemed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fulfilled_at TIMESTAMPTZ,
    reversed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT uk_loyalty_reward_redemption_idempotency UNIQUE (tenant_id, application_id, idempotency_key),
    CONSTRAINT uk_loyalty_reward_redemption_source UNIQUE (program_uuid, source_reference),
    CONSTRAINT chk_loyalty_reward_redemption_points CHECK (points_cost > 0),
    CONSTRAINT chk_loyalty_reward_redemption_status CHECK (status IN ('COMMITTED', 'REVERSED')),
    CONSTRAINT chk_loyalty_reward_fulfillment_status CHECK (fulfillment_status IN ('PENDING', 'ISSUED', 'MANUAL_REQUIRED', 'FAILED'))
);
CREATE INDEX IF NOT EXISTS idx_loyalty_reward_redemptions_scope_time
    ON loyalty_reward_redemptions (tenant_id, application_id, program_id, redeemed_at DESC);
CREATE INDEX IF NOT EXISTS idx_loyalty_reward_redemptions_reward
    ON loyalty_reward_redemptions (reward_id, status, redeemed_at DESC);
CREATE INDEX IF NOT EXISTS idx_loyalty_reward_redemptions_profile
    ON loyalty_reward_redemptions (tenant_id, application_id, program_id, profile_id, redeemed_at DESC);
