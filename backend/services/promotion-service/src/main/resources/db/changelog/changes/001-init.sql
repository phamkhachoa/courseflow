-- liquibase formatted sql
-- Generic incentive platform baseline. The schema intentionally avoids LMS-specific fields.

-- changeset courseflow:promotion-001-init
CREATE TABLE IF NOT EXISTS incentive_campaigns (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(80) NOT NULL,
    application_id VARCHAR(80) NOT NULL,
    code VARCHAR(120) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    incentive_type VARCHAR(40) NOT NULL DEFAULT 'PROMOTION',
    status VARCHAR(40) NOT NULL DEFAULT 'DRAFT',
    starts_at TIMESTAMPTZ,
    ends_at TIMESTAMPTZ,
    priority INTEGER NOT NULL DEFAULT 0,
    exclusive BOOLEAN NOT NULL DEFAULT FALSE,
    stackable BOOLEAN NOT NULL DEFAULT TRUE,
    coupon_required BOOLEAN NOT NULL DEFAULT FALSE,
    match_policy VARCHAR(20) NOT NULL DEFAULT 'ALL',
    currency VARCHAR(8),
    rules_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    actions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    max_redemptions INTEGER,
    max_redemptions_per_profile INTEGER,
    created_by VARCHAR(80),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at TIMESTAMPTZ,
    version BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT uk_incentive_campaign_scope_code UNIQUE (tenant_id, application_id, code),
    CONSTRAINT chk_incentive_campaign_status CHECK (status IN ('DRAFT', 'PUBLISHED', 'PAUSED', 'ARCHIVED')),
    CONSTRAINT chk_incentive_campaign_match_policy CHECK (match_policy IN ('ALL', 'ANY')),
    CONSTRAINT chk_incentive_campaign_dates CHECK (starts_at IS NULL OR ends_at IS NULL OR starts_at < ends_at),
    CONSTRAINT chk_incentive_campaign_redemption_limit CHECK (max_redemptions IS NULL OR max_redemptions >= 0),
    CONSTRAINT chk_incentive_campaign_profile_limit CHECK (max_redemptions_per_profile IS NULL OR max_redemptions_per_profile >= 0)
);
CREATE INDEX IF NOT EXISTS idx_incentive_campaigns_active
    ON incentive_campaigns (tenant_id, application_id, status, priority DESC, created_at, starts_at, ends_at);

CREATE TABLE IF NOT EXISTS incentive_coupons (
    id UUID PRIMARY KEY,
    campaign_id UUID NOT NULL REFERENCES incentive_campaigns(id),
    code VARCHAR(160) NOT NULL,
    normalized_code VARCHAR(160) NOT NULL,
    code_mask VARCHAR(80),
    status VARCHAR(40) NOT NULL DEFAULT 'ACTIVE',
    holder_profile_id VARCHAR(120),
    starts_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    max_redemptions INTEGER,
    max_redemptions_per_profile INTEGER,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT uk_incentive_coupon_campaign_code UNIQUE (campaign_id, normalized_code),
    CONSTRAINT chk_incentive_coupon_status CHECK (status IN ('ACTIVE', 'PAUSED', 'REDEEMED', 'EXPIRED', 'VOID')),
    CONSTRAINT chk_incentive_coupon_dates CHECK (starts_at IS NULL OR expires_at IS NULL OR starts_at < expires_at),
    CONSTRAINT chk_incentive_coupon_limit CHECK (max_redemptions IS NULL OR max_redemptions >= 0),
    CONSTRAINT chk_incentive_coupon_profile_limit CHECK (max_redemptions_per_profile IS NULL OR max_redemptions_per_profile >= 0)
);
CREATE INDEX IF NOT EXISTS idx_incentive_coupons_normalized_code
    ON incentive_coupons (normalized_code, status);

CREATE TABLE IF NOT EXISTS incentive_quota_counters (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(80) NOT NULL,
    application_id VARCHAR(80) NOT NULL,
    scope_type VARCHAR(40) NOT NULL,
    scope_id VARCHAR(120) NOT NULL,
    profile_id VARCHAR(120) NOT NULL DEFAULT '*',
    limit_count INTEGER NOT NULL,
    used_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT uk_incentive_quota_scope UNIQUE (tenant_id, application_id, scope_type, scope_id, profile_id),
    CONSTRAINT chk_incentive_quota_scope_type CHECK (scope_type IN ('CAMPAIGN', 'COUPON', 'CAMPAIGN_PROFILE', 'COUPON_PROFILE')),
    CONSTRAINT chk_incentive_quota_limit CHECK (limit_count >= 0),
    CONSTRAINT chk_incentive_quota_used CHECK (used_count >= 0 AND used_count <= limit_count)
);

CREATE TABLE IF NOT EXISTS incentive_reservations (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(80) NOT NULL,
    application_id VARCHAR(80) NOT NULL,
    campaign_id UUID NOT NULL REFERENCES incentive_campaigns(id),
    coupon_id UUID REFERENCES incentive_coupons(id),
    profile_id VARCHAR(120) NOT NULL,
    external_reference VARCHAR(160),
    status VARCHAR(40) NOT NULL DEFAULT 'RESERVED',
    effects_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    request_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    request_hash VARCHAR(128) NOT NULL,
    reserved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    committed_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    failure_reason VARCHAR(120),
    version BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT chk_incentive_reservation_status CHECK (status IN ('RESERVED', 'REDEEMED', 'CANCELLED', 'EXPIRED', 'FAILED'))
);
CREATE INDEX IF NOT EXISTS idx_incentive_reservations_profile
    ON incentive_reservations (tenant_id, application_id, profile_id, status);
CREATE INDEX IF NOT EXISTS idx_incentive_reservations_expiry
    ON incentive_reservations (status, expires_at);
CREATE INDEX IF NOT EXISTS idx_incentive_reservations_external_ref
    ON incentive_reservations (tenant_id, application_id, external_reference);

CREATE TABLE IF NOT EXISTS incentive_redemptions (
    id UUID PRIMARY KEY,
    reservation_id UUID REFERENCES incentive_reservations(id),
    tenant_id VARCHAR(80) NOT NULL,
    application_id VARCHAR(80) NOT NULL,
    campaign_id UUID NOT NULL REFERENCES incentive_campaigns(id),
    coupon_id UUID REFERENCES incentive_coupons(id),
    profile_id VARCHAR(120) NOT NULL,
    external_reference VARCHAR(160),
    status VARCHAR(40) NOT NULL DEFAULT 'REDEEMED',
    effects_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    request_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    request_hash VARCHAR(128) NOT NULL,
    redeemed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reversed_at TIMESTAMPTZ,
    reversed_by VARCHAR(80),
    version BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT uk_incentive_redemption_reservation UNIQUE (reservation_id),
    CONSTRAINT chk_incentive_redemption_status CHECK (status IN ('REDEEMED', 'REVERSED'))
);
CREATE INDEX IF NOT EXISTS idx_incentive_redemptions_campaign_profile
    ON incentive_redemptions (campaign_id, profile_id, status);
CREATE INDEX IF NOT EXISTS idx_incentive_redemptions_coupon_profile
    ON incentive_redemptions (coupon_id, profile_id, status);
CREATE INDEX IF NOT EXISTS idx_incentive_redemptions_external_ref
    ON incentive_redemptions (tenant_id, application_id, external_reference);

CREATE TABLE IF NOT EXISTS incentive_ledger_entries (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(80) NOT NULL,
    application_id VARCHAR(80) NOT NULL,
    entry_type VARCHAR(40) NOT NULL,
    reservation_id UUID REFERENCES incentive_reservations(id),
    redemption_id UUID REFERENCES incentive_redemptions(id),
    campaign_id UUID NOT NULL REFERENCES incentive_campaigns(id),
    coupon_id UUID REFERENCES incentive_coupons(id),
    profile_id VARCHAR(120) NOT NULL,
    external_reference VARCHAR(160),
    effect_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_incentive_ledger_entry_type CHECK (entry_type IN ('RESERVE', 'COMMIT', 'CANCEL', 'EXPIRE', 'REVERSE'))
);
CREATE INDEX IF NOT EXISTS idx_incentive_ledger_profile
    ON incentive_ledger_entries (tenant_id, application_id, profile_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_incentive_ledger_reservation
    ON incentive_ledger_entries (reservation_id, created_at DESC);

CREATE TABLE IF NOT EXISTS incentive_idempotency_keys (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(80) NOT NULL,
    application_id VARCHAR(80) NOT NULL,
    operation VARCHAR(40) NOT NULL,
    idempotency_key VARCHAR(160) NOT NULL,
    request_hash VARCHAR(128) NOT NULL,
    response_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(40) NOT NULL DEFAULT 'SUCCEEDED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT uk_incentive_idempotency_key UNIQUE (tenant_id, application_id, operation, idempotency_key),
    CONSTRAINT chk_incentive_idempotency_status CHECK (status IN ('SUCCEEDED', 'FAILED'))
);
CREATE INDEX IF NOT EXISTS idx_incentive_idempotency_expiry
    ON incentive_idempotency_keys (expires_at);

CREATE TABLE IF NOT EXISTS incentive_audit_events (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(80),
    application_id VARCHAR(80),
    aggregate_id VARCHAR(120) NOT NULL,
    aggregate_type VARCHAR(80) NOT NULL,
    action VARCHAR(80) NOT NULL,
    actor_id VARCHAR(80),
    note TEXT,
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_incentive_audit_aggregate
    ON incentive_audit_events (aggregate_type, aggregate_id, created_at DESC);

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

-- changeset courseflow:promotion-900-demo-data context=demo
INSERT INTO incentive_campaigns (
    id, tenant_id, application_id, code, name, description, incentive_type, status,
    starts_at, ends_at, priority, exclusive, stackable, coupon_required, match_policy,
    currency, rules_json, actions_json, max_redemptions, max_redemptions_per_profile,
    created_by, published_at
) VALUES (
    'b1000000-0000-0000-0000-000000000001',
    'courseflow',
    'lms',
    'WELCOME10',
    'Welcome 10 percent off',
    'Generic demo campaign: 10 percent off when order total reaches 100 and coupon WELCOME10 is supplied.',
    'PROMOTION',
    'PUBLISHED',
    NOW() - INTERVAL '1 day',
    NOW() + INTERVAL '90 days',
    100,
    FALSE,
    TRUE,
    TRUE,
    'ALL',
    'USD',
    '[{"schemaVersion":1,"type":"MIN_ORDER_AMOUNT","parameters":{"amount":100,"currency":"USD"}}]'::jsonb,
    '[{"schemaVersion":1,"type":"ORDER_PERCENT_OFF","parameters":{"percent":10,"maxAmount":50}}]'::jsonb,
    10000,
    1,
    'seed',
    NOW()
) ON CONFLICT (tenant_id, application_id, code) DO NOTHING;

INSERT INTO incentive_coupons (id, campaign_id, code, normalized_code, code_mask, status, max_redemptions, max_redemptions_per_profile)
VALUES (
    'b2000000-0000-0000-0000-000000000001',
    'b1000000-0000-0000-0000-000000000001',
    'WELCOME10',
    'WELCOME10',
    'WEL****10',
    'ACTIVE',
    10000,
    1
) ON CONFLICT (campaign_id, normalized_code) DO NOTHING;
