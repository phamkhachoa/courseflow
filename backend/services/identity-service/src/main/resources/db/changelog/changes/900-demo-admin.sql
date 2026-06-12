-- liquibase formatted sql
-- changeset courseflow:identity-900-demo-admin context:demo splitStatements:false
-- Local/demo bootstrap account for the admin SPA.
-- Email: admin@courseflow.local
-- Password: password

WITH upsert_user AS (
    INSERT INTO users (
        email,
        email_verified,
        password_hash,
        full_name,
        status,
        mfa_enabled,
        must_change_password,
        created_by
    )
    VALUES (
        'admin@courseflow.local',
        TRUE,
        '$2a$12$9lNOgMCJhc3V1Fudu/xf8.lgFwFcKzP2MOCuMcbt.c4h9u2mUhhYy',
        'CourseFlow Admin',
        'ACTIVE',
        FALSE,
        FALSE,
        'demo-seed'
    )
    ON CONFLICT (LOWER(email)) DO UPDATE SET
        password_hash = EXCLUDED.password_hash,
        email_verified = TRUE,
        status = 'ACTIVE',
        mfa_enabled = FALSE,
        must_change_password = FALSE,
        full_name = EXCLUDED.full_name,
        last_modified_on = NOW(),
        last_modified_by = 'demo-seed'
    RETURNING id
), selected_user AS (
    SELECT id FROM upsert_user
    UNION ALL
    SELECT id FROM users WHERE LOWER(email) = LOWER('admin@courseflow.local')
    LIMIT 1
)
INSERT INTO user_role_assignments (user_id, role_id, scope_type, scope_id, granted_by)
SELECT selected_user.id, roles.id, 'PLATFORM', NULL, 'demo-seed'
FROM selected_user
JOIN roles ON roles.code = 'ADMIN'
ON CONFLICT (user_id, role_id, scope_type, COALESCE(scope_id, ''))
WHERE revoked_at IS NULL DO NOTHING;
