-- liquibase formatted sql

-- changeset courseflow:loyalty-009-tiers
CREATE TABLE IF NOT EXISTS loyalty_tier_policies (
    id UUID PRIMARY KEY,
    program_uuid UUID NOT NULL REFERENCES loyalty_programs(id),
    tenant_id VARCHAR(80) NOT NULL,
    application_id VARCHAR(80) NOT NULL,
    program_id VARCHAR(120) NOT NULL,
    tier_code VARCHAR(80) NOT NULL,
    name VARCHAR(160) NOT NULL,
    rank INTEGER NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'ACTIVE',
    qualification_points BIGINT NOT NULL,
    qualification_window_days INTEGER NOT NULL DEFAULT 365,
    downgrade_grace_days INTEGER NOT NULL DEFAULT 30,
    benefits_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by VARCHAR(160),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT uk_loyalty_tier_policy_code UNIQUE (program_uuid, tier_code),
    CONSTRAINT uk_loyalty_tier_policy_rank UNIQUE (program_uuid, rank),
    CONSTRAINT chk_loyalty_tier_policy_status CHECK (status IN ('DRAFT', 'ACTIVE', 'SUSPENDED', 'ARCHIVED')),
    CONSTRAINT chk_loyalty_tier_policy_rank CHECK (rank > 0),
    CONSTRAINT chk_loyalty_tier_policy_points CHECK (qualification_points >= 0),
    CONSTRAINT chk_loyalty_tier_policy_window CHECK (qualification_window_days > 0),
    CONSTRAINT chk_loyalty_tier_policy_grace CHECK (downgrade_grace_days >= 0)
);
CREATE INDEX IF NOT EXISTS idx_loyalty_tier_policy_scope
    ON loyalty_tier_policies (tenant_id, application_id, program_id, status, rank);

CREATE TABLE IF NOT EXISTS loyalty_tier_states (
    id UUID PRIMARY KEY,
    account_id UUID NOT NULL REFERENCES loyalty_accounts(id),
    program_uuid UUID NOT NULL REFERENCES loyalty_programs(id),
    tenant_id VARCHAR(80) NOT NULL,
    application_id VARCHAR(80) NOT NULL,
    program_id VARCHAR(120) NOT NULL,
    profile_id VARCHAR(160) NOT NULL,
    tier_policy_id UUID REFERENCES loyalty_tier_policies(id),
    tier_code VARCHAR(80) NOT NULL DEFAULT 'BASE',
    tier_name VARCHAR(160) NOT NULL DEFAULT 'Base',
    tier_rank INTEGER NOT NULL DEFAULT 0,
    qualification_points BIGINT NOT NULL DEFAULT 0,
    qualification_window_days INTEGER,
    qualification_window_started_at TIMESTAMPTZ,
    qualification_window_ends_at TIMESTAMPTZ,
    current_period_started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    qualified_at TIMESTAMPTZ,
    grace_until TIMESTAMPTZ,
    next_tier_policy_id UUID REFERENCES loyalty_tier_policies(id),
    next_tier_code VARCHAR(80),
    next_tier_name VARCHAR(160),
    next_tier_rank INTEGER,
    next_tier_points_required BIGINT,
    points_to_next BIGINT,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT uk_loyalty_tier_state_account UNIQUE (account_id),
    CONSTRAINT chk_loyalty_tier_state_rank CHECK (tier_rank >= 0),
    CONSTRAINT chk_loyalty_tier_state_points CHECK (qualification_points >= 0)
);
CREATE INDEX IF NOT EXISTS idx_loyalty_tier_state_scope
    ON loyalty_tier_states (tenant_id, application_id, program_id, profile_id);
CREATE INDEX IF NOT EXISTS idx_loyalty_tier_state_program_rank
    ON loyalty_tier_states (program_uuid, tier_rank, evaluated_at DESC);
