-- liquibase formatted sql
-- Production runtime contract: tenant/application registry and immutable campaign snapshots.

-- changeset courseflow:promotion-003-production-contract
CREATE TABLE IF NOT EXISTS incentive_applications (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(80) NOT NULL,
    application_id VARCHAR(80) NOT NULL,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'DRAFT',
    created_by VARCHAR(80),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT uk_incentive_application_scope UNIQUE (tenant_id, application_id),
    CONSTRAINT chk_incentive_application_status CHECK (status IN ('DRAFT', 'ACTIVE', 'SUSPENDED', 'ARCHIVED'))
);
CREATE INDEX IF NOT EXISTS idx_incentive_applications_status
    ON incentive_applications (tenant_id, application_id, status);

CREATE TABLE IF NOT EXISTS incentive_application_client_bindings (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(80) NOT NULL,
    application_id VARCHAR(80) NOT NULL,
    client_id VARCHAR(160) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'ACTIVE',
    allowed_operations JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_by VARCHAR(80),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT uk_incentive_application_client UNIQUE (tenant_id, application_id, client_id),
    CONSTRAINT chk_incentive_application_client_status CHECK (status IN ('ACTIVE', 'SUSPENDED'))
);
CREATE INDEX IF NOT EXISTS idx_incentive_application_client_lookup
    ON incentive_application_client_bindings (tenant_id, application_id, client_id, status);

CREATE TABLE IF NOT EXISTS incentive_campaign_versions (
    id UUID PRIMARY KEY,
    campaign_id UUID NOT NULL REFERENCES incentive_campaigns(id),
    tenant_id VARCHAR(80) NOT NULL,
    application_id VARCHAR(80) NOT NULL,
    code VARCHAR(120) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    incentive_type VARCHAR(40) NOT NULL DEFAULT 'PROMOTION',
    version_number INTEGER NOT NULL,
    version_status VARCHAR(40) NOT NULL DEFAULT 'DRAFT',
    active_snapshot BOOLEAN NOT NULL DEFAULT FALSE,
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
    submitted_by VARCHAR(80),
    reviewed_by VARCHAR(80),
    published_by VARCHAR(80),
    review_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    submitted_at TIMESTAMPTZ,
    reviewed_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    version BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT uk_incentive_campaign_version UNIQUE (campaign_id, version_number),
    CONSTRAINT chk_incentive_campaign_version_status CHECK (
        version_status IN ('DRAFT', 'SUBMITTED', 'APPROVED', 'REJECTED', 'PUBLISHED', 'SUPERSEDED')
    ),
    CONSTRAINT chk_incentive_campaign_version_match_policy CHECK (match_policy IN ('ALL', 'ANY')),
    CONSTRAINT chk_incentive_campaign_version_dates CHECK (starts_at IS NULL OR ends_at IS NULL OR starts_at < ends_at),
    CONSTRAINT chk_incentive_campaign_version_redemption_limit CHECK (max_redemptions IS NULL OR max_redemptions >= 0),
    CONSTRAINT chk_incentive_campaign_version_profile_limit CHECK (max_redemptions_per_profile IS NULL OR max_redemptions_per_profile >= 0)
);
CREATE UNIQUE INDEX IF NOT EXISTS uk_incentive_campaign_active_snapshot
    ON incentive_campaign_versions (campaign_id)
    WHERE active_snapshot = TRUE;
CREATE INDEX IF NOT EXISTS idx_incentive_campaign_versions_runtime
    ON incentive_campaign_versions (
        tenant_id, application_id, active_snapshot, version_status,
        priority DESC, created_at, starts_at, ends_at
    );
CREATE INDEX IF NOT EXISTS idx_incentive_campaign_versions_review
    ON incentive_campaign_versions (tenant_id, application_id, version_status, created_at DESC);

ALTER TABLE incentive_reservations
    ADD COLUMN IF NOT EXISTS campaign_version INTEGER,
    ADD COLUMN IF NOT EXISTS quota_snapshot_json JSONB NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE incentive_redemptions
    ADD COLUMN IF NOT EXISTS campaign_version INTEGER;

ALTER TABLE incentive_ledger_entries
    ADD COLUMN IF NOT EXISTS campaign_version INTEGER;

INSERT INTO incentive_applications (
    id, tenant_id, application_id, name, status, created_by
)
SELECT md5(c.tenant_id || ':' || c.application_id)::uuid, c.tenant_id, c.application_id, c.application_id, 'ACTIVE', 'migration'
FROM incentive_campaigns c
GROUP BY c.tenant_id, c.application_id
ON CONFLICT (tenant_id, application_id) DO NOTHING;

INSERT INTO incentive_campaign_versions (
    id, campaign_id, tenant_id, application_id, code, name, description, incentive_type,
    version_number, version_status, active_snapshot, starts_at, ends_at, priority, exclusive,
    stackable, coupon_required, match_policy, currency, rules_json, actions_json,
    max_redemptions, max_redemptions_per_profile, created_by, published_by, created_at, published_at
)
SELECT
    md5(c.id::text || ':1')::uuid,
    c.id,
    c.tenant_id,
    c.application_id,
    c.code,
    c.name,
    c.description,
    c.incentive_type,
    1,
    CASE WHEN c.status = 'PUBLISHED' THEN 'PUBLISHED' ELSE 'DRAFT' END,
    CASE WHEN c.status = 'PUBLISHED' THEN TRUE ELSE FALSE END,
    c.starts_at,
    c.ends_at,
    c.priority,
    c.exclusive,
    c.stackable,
    c.coupon_required,
    c.match_policy,
    c.currency,
    c.rules_json,
    c.actions_json,
    c.max_redemptions,
    c.max_redemptions_per_profile,
    c.created_by,
    CASE WHEN c.status = 'PUBLISHED' THEN COALESCE(c.created_by, 'migration') ELSE NULL END,
    c.created_at,
    c.published_at
FROM incentive_campaigns c
WHERE NOT EXISTS (
    SELECT 1
    FROM incentive_campaign_versions v
    WHERE v.campaign_id = c.id
);

UPDATE incentive_reservations r
SET campaign_version = v.version_number
FROM incentive_campaign_versions v
WHERE r.campaign_id = v.campaign_id
  AND r.campaign_version IS NULL
  AND v.version_number = 1;

UPDATE incentive_redemptions r
SET campaign_version = v.version_number
FROM incentive_campaign_versions v
WHERE r.campaign_id = v.campaign_id
  AND r.campaign_version IS NULL
  AND v.version_number = 1;

UPDATE incentive_ledger_entries l
SET campaign_version = v.version_number
FROM incentive_campaign_versions v
WHERE l.campaign_id = v.campaign_id
  AND l.campaign_version IS NULL
  AND v.version_number = 1;
