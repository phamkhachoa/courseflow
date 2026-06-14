-- liquibase formatted sql
-- Client binding operations are fail-closed: an empty array grants no operation.

-- changeset courseflow:promotion-011-client-binding-fail-closed-normalize
UPDATE incentive_application_client_bindings
SET allowed_operations = '[]'::jsonb,
    updated_at = NOW()
WHERE allowed_operations IS NULL
   OR jsonb_typeof(allowed_operations) <> 'array';

-- changeset courseflow:promotion-011-client-binding-fail-closed-constraint splitStatements:false
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_incentive_application_client_allowed_operations_array'
    ) THEN
        ALTER TABLE incentive_application_client_bindings
            ADD CONSTRAINT chk_incentive_application_client_allowed_operations_array
            CHECK (jsonb_typeof(allowed_operations) = 'array');
    END IF;
END $$;
