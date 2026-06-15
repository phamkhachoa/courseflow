-- liquibase formatted sql
-- changeset courseflow:loyalty-007-promotion-point-effect-reconciliation

CREATE TABLE IF NOT EXISTS loyalty_promotion_point_effects (
    id UUID PRIMARY KEY,
    source_topic VARCHAR(240) NOT NULL,
    source_event_type VARCHAR(160) NOT NULL,
    event_id VARCHAR(180) NOT NULL,
    redemption_id VARCHAR(180) NOT NULL,
    effect_id VARCHAR(240) NOT NULL,
    expected_entry_type VARCHAR(40) NOT NULL,
    tenant_id VARCHAR(80) NOT NULL,
    application_id VARCHAR(80) NOT NULL,
    program_id VARCHAR(120) NOT NULL,
    profile_id VARCHAR(160) NOT NULL,
    points_delta BIGINT NOT NULL,
    original_source_reference VARCHAR(180) NOT NULL,
    expected_idempotency_key VARCHAR(180) NOT NULL,
    correlation_id VARCHAR(160),
    payload_hash VARCHAR(80) NOT NULL,
    event_occurred_at TIMESTAMPTZ,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT uk_loyalty_promotion_point_effect UNIQUE (
        source_event_type,
        event_id,
        effect_id,
        expected_entry_type
    ),
    CONSTRAINT chk_loyalty_promotion_point_effect_entry_type CHECK (
        expected_entry_type IN ('EARN', 'REVERSE')
    )
);

CREATE INDEX IF NOT EXISTS idx_loyalty_promotion_point_effect_scope
    ON loyalty_promotion_point_effects (
        tenant_id,
        application_id,
        program_id,
        profile_id,
        observed_at DESC
    );
CREATE INDEX IF NOT EXISTS idx_loyalty_promotion_point_effect_redemption
    ON loyalty_promotion_point_effects (redemption_id, expected_entry_type);
CREATE INDEX IF NOT EXISTS idx_loyalty_promotion_point_effect_source_ref
    ON loyalty_promotion_point_effects (original_source_reference, expected_entry_type);
