-- liquibase formatted sql
-- Production invariants for review/coupon hardening.

-- changeset courseflow:promotion-006-production-invariants
UPDATE incentive_application_client_bindings
SET allowed_operations = (
    CASE
        WHEN jsonb_exists(allowed_operations, 'reverse') THEN allowed_operations
        ELSE allowed_operations || '["reverse"]'::jsonb
    END
)
WHERE status = 'ACTIVE'
  AND client_id = 'api-gateway'
  AND allowed_operations <> '[]'::jsonb;

CREATE UNIQUE INDEX IF NOT EXISTS uk_incentive_campaign_version_number
    ON incentive_campaign_versions (campaign_id, version_number);

ALTER TABLE incentive_campaign_versions
    DROP CONSTRAINT IF EXISTS chk_incentive_campaign_version_active_published,
    ADD CONSTRAINT chk_incentive_campaign_version_active_published
        CHECK (active_snapshot = FALSE OR version_status = 'PUBLISHED');

ALTER TABLE incentive_reservations
    DROP CONSTRAINT IF EXISTS fk_incentive_reservation_campaign_version,
    ADD CONSTRAINT fk_incentive_reservation_campaign_version
        FOREIGN KEY (campaign_id, campaign_version)
        REFERENCES incentive_campaign_versions (campaign_id, version_number);

ALTER TABLE incentive_redemptions
    DROP CONSTRAINT IF EXISTS fk_incentive_redemption_campaign_version,
    ADD CONSTRAINT fk_incentive_redemption_campaign_version
        FOREIGN KEY (campaign_id, campaign_version)
        REFERENCES incentive_campaign_versions (campaign_id, version_number);

ALTER TABLE incentive_ledger_entries
    DROP CONSTRAINT IF EXISTS fk_incentive_ledger_campaign_version,
    ADD CONSTRAINT fk_incentive_ledger_campaign_version
        FOREIGN KEY (campaign_id, campaign_version)
        REFERENCES incentive_campaign_versions (campaign_id, version_number);

CREATE UNIQUE INDEX IF NOT EXISTS uk_incentive_active_reservation_external_ref
    ON incentive_reservations (tenant_id, application_id, external_reference)
    WHERE external_reference IS NOT NULL
      AND status IN ('RESERVED', 'REDEEMED');

CREATE UNIQUE INDEX IF NOT EXISTS uk_incentive_redemption_external_ref
    ON incentive_redemptions (tenant_id, application_id, external_reference)
    WHERE external_reference IS NOT NULL
      AND status = 'REDEEMED';
