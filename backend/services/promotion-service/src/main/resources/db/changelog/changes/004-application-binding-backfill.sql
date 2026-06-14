-- liquibase formatted sql
-- Make runtime application binding fail-closed while preserving gateway traffic for migrated apps.

-- changeset courseflow:promotion-004-application-binding-backfill
INSERT INTO incentive_application_client_bindings (
    id, tenant_id, application_id, client_id, status, allowed_operations, created_by
)
SELECT
    md5(a.tenant_id || ':' || a.application_id || ':api-gateway')::uuid,
    a.tenant_id,
    a.application_id,
    'api-gateway',
    'ACTIVE',
    '["evaluate","reserve","commit","cancel","admin"]'::jsonb,
    'migration'
FROM incentive_applications a
WHERE a.status = 'ACTIVE'
ON CONFLICT (tenant_id, application_id, client_id) DO NOTHING;
