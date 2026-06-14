-- liquibase formatted sql

-- changeset courseflow:promotion-009-coupon-inventory-indexes
CREATE INDEX IF NOT EXISTS idx_incentive_coupons_campaign_status_code
    ON incentive_coupons (campaign_id, status, normalized_code);

CREATE INDEX IF NOT EXISTS idx_incentive_campaigns_scope_id
    ON incentive_campaigns (tenant_id, application_id, id);
