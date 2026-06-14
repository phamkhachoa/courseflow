-- liquibase formatted sql

-- changeset courseflow:promotion-021-retention-approval-query-indexes
CREATE INDEX IF NOT EXISTS idx_retention_approval_tenant_app_status_time
    ON incentive_retention_approvals (tenant_id, application_id, status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_retention_approval_global_status_time
    ON incentive_retention_approvals (status, created_at DESC)
    WHERE tenant_id IS NULL AND application_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_retention_approval_dry_run_time
    ON incentive_retention_approvals (dry_run_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_retention_approval_ticket_time
    ON incentive_retention_approvals (lower(change_ticket), created_at DESC);
