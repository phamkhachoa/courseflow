-- liquibase formatted sql

-- changeset courseflow:promotion-014-retention-operation-scope-key-normalization
UPDATE incentive_retention_operations
SET scope_key = CASE
    WHEN tenant_id IS NULL AND application_id IS NULL THEN 'GLOBAL:0:|APP:0:'
    ELSE 'TENANT:' || char_length(tenant_id)::text || ':' || tenant_id
        || '|APP:' || char_length(application_id)::text || ':' || application_id
END;

CREATE INDEX IF NOT EXISTS idx_incentive_retention_operations_scope_key_created
    ON incentive_retention_operations (scope_key, created_at);
