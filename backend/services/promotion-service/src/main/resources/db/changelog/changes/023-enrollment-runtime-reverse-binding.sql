-- liquibase formatted sql
-- Enrollment-service must reverse applied coupon redemptions when an enrollment is dropped.

-- changeset courseflow:promotion-023-enrollment-runtime-reverse-binding
UPDATE incentive_application_client_bindings
SET allowed_operations = CASE
        WHEN jsonb_exists(COALESCE(allowed_operations, '[]'::jsonb), 'reverse')
            THEN COALESCE(allowed_operations, '[]'::jsonb)
        ELSE COALESCE(allowed_operations, '[]'::jsonb) || '["reverse"]'::jsonb
    END,
    status = 'ACTIVE',
    updated_at = NOW()
WHERE client_id = 'enrollment-service'
  AND status = 'ACTIVE';

INSERT INTO incentive_application_client_bindings (
    id, tenant_id, application_id, client_id, status, allowed_operations, created_by
)
SELECT
    md5(a.tenant_id || ':' || a.application_id || ':enrollment-service')::uuid,
    a.tenant_id,
    a.application_id,
    'enrollment-service',
    'ACTIVE',
    '["evaluate","reserve","commit","cancel","reverse"]'::jsonb,
    'migration'
FROM incentive_applications a
WHERE a.status = 'ACTIVE'
ON CONFLICT (tenant_id, application_id, client_id)
DO UPDATE SET
    status = 'ACTIVE',
    allowed_operations = (
        SELECT jsonb_agg(DISTINCT value ORDER BY value)
        FROM jsonb_array_elements_text(
            COALESCE(incentive_application_client_bindings.allowed_operations, '[]'::jsonb)
            || '["evaluate","reserve","commit","cancel","reverse"]'::jsonb
        ) AS operations(value)
    ),
    updated_at = NOW();
