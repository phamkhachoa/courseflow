-- liquibase formatted sql
-- changeset courseflow:analytics-002-marketing-funnel-metrics
CREATE TABLE IF NOT EXISTS marketing_funnel_metrics (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(80) NOT NULL,
    application_id VARCHAR(80) NOT NULL,
    campaign_code VARCHAR(120),
    source VARCHAR(120),
    stage VARCHAR(80) NOT NULL,
    bucket_date DATE NOT NULL,
    event_count BIGINT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_marketing_funnel_metric_key
    ON marketing_funnel_metrics (
        tenant_id,
        application_id,
        COALESCE(campaign_code, ''),
        COALESCE(source, ''),
        stage,
        bucket_date
    );

CREATE INDEX IF NOT EXISTS idx_marketing_funnel_scope
    ON marketing_funnel_metrics (tenant_id, application_id, bucket_date);

CREATE INDEX IF NOT EXISTS idx_marketing_funnel_campaign_source
    ON marketing_funnel_metrics (tenant_id, application_id, campaign_code, source, stage);

CREATE TABLE IF NOT EXISTS marketing_funnel_event_receipts (
    id UUID PRIMARY KEY,
    source_event_id UUID NOT NULL,
    tenant_id VARCHAR(80) NOT NULL,
    application_id VARCHAR(80) NOT NULL,
    campaign_code VARCHAR(120),
    source VARCHAR(120),
    stage VARCHAR(80) NOT NULL,
    bucket_date DATE NOT NULL,
    event_count BIGINT NOT NULL DEFAULT 1,
    request_hash VARCHAR(96) NOT NULL,
    actor_id VARCHAR(120),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_marketing_funnel_event_receipt_source
    ON marketing_funnel_event_receipts (source_event_id);

CREATE INDEX IF NOT EXISTS idx_marketing_funnel_event_receipts_scope
    ON marketing_funnel_event_receipts (tenant_id, application_id, bucket_date);
