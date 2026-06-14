-- liquibase formatted sql
-- Enrollment-service is a trusted source client for learner enrollment promotion facts.

-- changeset courseflow:promotion-022-enrollment-runtime-binding
INSERT INTO incentive_application_client_bindings (
    id, tenant_id, application_id, client_id, status, allowed_operations, created_by
)
SELECT
    md5(a.tenant_id || ':' || a.application_id || ':enrollment-service')::uuid,
    a.tenant_id,
    a.application_id,
    'enrollment-service',
    'ACTIVE',
    '["evaluate","reserve","commit","cancel"]'::jsonb,
    'migration'
FROM incentive_applications a
WHERE a.status = 'ACTIVE'
ON CONFLICT (tenant_id, application_id, client_id)
DO UPDATE SET
    status = 'ACTIVE',
    allowed_operations = '["evaluate","reserve","commit","cancel"]'::jsonb,
    updated_at = NOW();
