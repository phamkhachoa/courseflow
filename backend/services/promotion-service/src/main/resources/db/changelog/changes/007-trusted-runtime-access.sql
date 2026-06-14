-- liquibase formatted sql
-- Fail closed for browser/user runtime traffic. Runtime facts must come from a bound service actor.

-- changeset courseflow:promotion-007-trusted-runtime-access
UPDATE incentive_application_client_bindings
SET allowed_operations = '["admin","reverse"]'::jsonb,
    updated_at = NOW()
WHERE client_id = 'api-gateway'
  AND status = 'ACTIVE';
