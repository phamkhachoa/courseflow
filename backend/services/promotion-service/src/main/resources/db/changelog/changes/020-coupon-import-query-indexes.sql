-- liquibase formatted sql

-- changeset courseflow:promotion-020-coupon-import-query-indexes
CREATE INDEX IF NOT EXISTS idx_coupon_import_operation_tenant_app_time
    ON incentive_coupon_import_operations (tenant_id, application_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_coupon_import_operation_approval_time
    ON incentive_coupon_import_operations (approval_id, created_at DESC)
    WHERE approval_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_coupon_import_operation_dry_run_time
    ON incentive_coupon_import_operations (dry_run_id, created_at DESC);
