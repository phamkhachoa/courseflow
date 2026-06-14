-- liquibase formatted sql
-- Production operations contract: audit explorer, version workspace, reversal hardening.

-- changeset courseflow:promotion-005-production-operations-contract
ALTER TABLE incentive_audit_events
    ADD COLUMN IF NOT EXISTS correlation_id VARCHAR(120),
    ADD COLUMN IF NOT EXISTS source_client_id VARCHAR(160);

CREATE INDEX IF NOT EXISTS idx_incentive_audit_tenant_app_time
    ON incentive_audit_events (tenant_id, application_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_incentive_audit_action_time
    ON incentive_audit_events (action, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_incentive_audit_actor_time
    ON incentive_audit_events (actor_id, created_at DESC);

ALTER TABLE incentive_campaign_versions
    ADD COLUMN IF NOT EXISTS rollback_source_version INTEGER;

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

ALTER TABLE incentive_reservations
    ALTER COLUMN campaign_version SET NOT NULL;
ALTER TABLE incentive_redemptions
    ALTER COLUMN campaign_version SET NOT NULL;
ALTER TABLE incentive_ledger_entries
    ALTER COLUMN campaign_version SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uk_outbox_incentive_redemption_reversed
    ON outbox_events (aggregate_id, event_type)
    WHERE aggregate_type = 'incentive-redemption' AND event_type = 'incentive.redemption.reversed';
