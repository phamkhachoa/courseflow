-- liquibase formatted sql

-- changeset courseflow:promotion-013-retention-operation-scoped-idempotency
ALTER TABLE incentive_retention_operations
    ADD COLUMN IF NOT EXISTS scope_key VARCHAR(180);

UPDATE incentive_retention_operations
SET scope_key = coalesce(tenant_id, 'GLOBAL') || '/' || coalesce(application_id, 'GLOBAL')
WHERE scope_key IS NULL;

ALTER TABLE incentive_retention_operations
    ALTER COLUMN scope_key SET NOT NULL;

ALTER TABLE incentive_retention_operations
    DROP CONSTRAINT IF EXISTS uq_incentive_retention_operation_idempotency,
    ADD CONSTRAINT uq_incentive_retention_operation_idempotency
        UNIQUE (policy_id, scope_key, idempotency_key);

CREATE INDEX IF NOT EXISTS idx_incentive_retention_operations_scope_key
    ON incentive_retention_operations (policy_id, scope_key, created_at);
