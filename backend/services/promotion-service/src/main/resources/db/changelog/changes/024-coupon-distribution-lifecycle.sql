-- liquibase formatted sql

-- changeset courseflow:promotion-024-coupon-distribution-lifecycle
CREATE TABLE IF NOT EXISTS incentive_coupon_distributions (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(80) NOT NULL,
    application_id VARCHAR(80) NOT NULL,
    campaign_id UUID NOT NULL REFERENCES incentive_campaigns(id),
    name VARCHAR(255) NOT NULL,
    source_type VARCHAR(40) NOT NULL,
    source_reference VARCHAR(160),
    status VARCHAR(40) NOT NULL DEFAULT 'PENDING_APPROVAL',
    notify_learners BOOLEAN NOT NULL DEFAULT FALSE,
    starts_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    max_redemptions INTEGER,
    max_redemptions_per_profile INTEGER,
    recipient_count INTEGER NOT NULL DEFAULT 0,
    issued_count INTEGER NOT NULL DEFAULT 0,
    revoked_count INTEGER NOT NULL DEFAULT 0,
    preview_hash VARCHAR(160) NOT NULL,
    reason VARCHAR(500),
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by VARCHAR(80),
    approved_by VARCHAR(80),
    issued_by VARCHAR(80),
    revoked_by VARCHAR(80),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMPTZ,
    issued_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT chk_coupon_distribution_source_type CHECK (
        source_type IN ('COHORT', 'SECTION', 'COURSE', 'SEGMENT', 'MANUAL')
    ),
    CONSTRAINT chk_coupon_distribution_status CHECK (
        status IN ('PENDING_APPROVAL', 'APPROVED', 'ISSUED', 'REVOKED')
    ),
    CONSTRAINT chk_coupon_distribution_dates CHECK (starts_at IS NULL OR expires_at IS NULL OR starts_at < expires_at),
    CONSTRAINT chk_coupon_distribution_limits CHECK (
        (max_redemptions IS NULL OR max_redemptions >= 0)
        AND (max_redemptions_per_profile IS NULL OR max_redemptions_per_profile >= 0)
        AND recipient_count >= 0
        AND issued_count >= 0
        AND revoked_count >= 0
    )
);

CREATE INDEX IF NOT EXISTS idx_coupon_distribution_tenant_app_time
    ON incentive_coupon_distributions (tenant_id, application_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_coupon_distribution_campaign_status
    ON incentive_coupon_distributions (campaign_id, status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_coupon_distribution_source
    ON incentive_coupon_distributions (tenant_id, application_id, source_type, source_reference);

CREATE TABLE IF NOT EXISTS incentive_coupon_distribution_recipients (
    id UUID PRIMARY KEY,
    distribution_id UUID NOT NULL REFERENCES incentive_coupon_distributions(id) ON DELETE CASCADE,
    tenant_id VARCHAR(80) NOT NULL,
    application_id VARCHAR(80) NOT NULL,
    campaign_id UUID NOT NULL REFERENCES incentive_campaigns(id),
    profile_id VARCHAR(120) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'PENDING',
    coupon_id UUID REFERENCES incentive_coupons(id),
    notification_status VARCHAR(40) NOT NULL DEFAULT 'SUPPRESSED',
    failure_reason VARCHAR(500),
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    issued_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT uk_coupon_distribution_recipient_profile UNIQUE (distribution_id, profile_id),
    CONSTRAINT chk_coupon_distribution_recipient_status CHECK (
        status IN ('PENDING', 'ISSUED', 'REVOKED', 'SKIPPED')
    ),
    CONSTRAINT chk_coupon_distribution_notification_status CHECK (
        notification_status IN ('SUPPRESSED', 'QUEUED')
    )
);

CREATE INDEX IF NOT EXISTS idx_coupon_distribution_recipient_distribution
    ON incentive_coupon_distribution_recipients (distribution_id, created_at ASC);

CREATE INDEX IF NOT EXISTS idx_coupon_distribution_recipient_profile
    ON incentive_coupon_distribution_recipients (tenant_id, application_id, profile_id, status);
