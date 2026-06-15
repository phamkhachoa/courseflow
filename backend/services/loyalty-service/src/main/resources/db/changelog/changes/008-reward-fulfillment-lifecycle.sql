-- changeset courseflow:loyalty-008-reward-fulfillment-lifecycle

ALTER TABLE loyalty_reward_redemptions
    ADD COLUMN IF NOT EXISTS fulfillment_provider VARCHAR(80),
    ADD COLUMN IF NOT EXISTS fulfillment_attempt_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS fulfillment_last_attempt_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS fulfillment_next_attempt_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS fulfillment_sla_due_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS fulfillment_error_class VARCHAR(160),
    ADD COLUMN IF NOT EXISTS fulfillment_error_message TEXT,
    ADD COLUMN IF NOT EXISTS fulfillment_callback_received_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS fulfillment_callback_payload_hash VARCHAR(128);

UPDATE loyalty_reward_redemptions
SET fulfillment_provider = COALESCE(fulfillment_provider, reward_snapshot_json ->> 'fulfillmentType', 'MANUAL')
WHERE fulfillment_provider IS NULL;

ALTER TABLE loyalty_reward_redemptions
    ALTER COLUMN fulfillment_provider SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_loyalty_reward_fulfillment_due
    ON loyalty_reward_redemptions (fulfillment_status, fulfillment_next_attempt_at)
    WHERE status = 'COMMITTED'
      AND fulfillment_status IN ('PENDING', 'FAILED')
      AND fulfillment_next_attempt_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_loyalty_reward_fulfillment_ref
    ON loyalty_reward_redemptions (fulfillment_provider, fulfillment_ref)
    WHERE fulfillment_ref IS NOT NULL;

CREATE TABLE IF NOT EXISTS loyalty_reward_fulfillment_attempts (
    id UUID PRIMARY KEY,
    redemption_id UUID NOT NULL REFERENCES loyalty_reward_redemptions(id),
    tenant_id VARCHAR(80) NOT NULL,
    application_id VARCHAR(80) NOT NULL,
    program_id VARCHAR(120) NOT NULL,
    profile_id VARCHAR(160) NOT NULL,
    reward_id UUID NOT NULL,
    reward_code VARCHAR(120) NOT NULL,
    provider VARCHAR(80) NOT NULL,
    attempt_number INTEGER NOT NULL,
    status VARCHAR(40) NOT NULL,
    fulfillment_ref VARCHAR(180),
    error_class VARCHAR(160),
    error_message TEXT,
    requested_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    next_attempt_at TIMESTAMPTZ,
    correlation_id VARCHAR(160),
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_loyalty_reward_fulfillment_attempt_status CHECK (
        status IN ('PENDING', 'ISSUED', 'MANUAL_REQUIRED', 'FAILED')
    )
);

CREATE INDEX IF NOT EXISTS idx_loyalty_reward_fulfillment_attempts_redemption
    ON loyalty_reward_fulfillment_attempts (redemption_id, attempt_number DESC);

CREATE INDEX IF NOT EXISTS idx_loyalty_reward_fulfillment_attempts_scope
    ON loyalty_reward_fulfillment_attempts (tenant_id, application_id, program_id, requested_at DESC);
