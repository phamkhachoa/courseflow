-- liquibase formatted sql
-- changeset courseflow:access-control-900-demo-access context:demo splitStatements:false

INSERT INTO access_users (id, email, status) VALUES
    (1, 'admin@courseflow.local', 'ACTIVE'),
    (2, 'instructor@courseflow.local', 'ACTIVE'),
    (3, 'student@courseflow.local', 'ACTIVE')
ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email, status = EXCLUDED.status, updated_at = NOW();

INSERT INTO external_identity_links (user_id, provider, issuer, subject, email_at_link, email_verified_at_link, status)
VALUES
    (1, 'legacy-courseflow', 'courseflow-identity', 'admin@courseflow.local', 'admin@courseflow.local', TRUE, 'ACTIVE'),
    (2, 'legacy-courseflow', 'courseflow-identity', 'instructor@courseflow.local', 'instructor@courseflow.local', TRUE, 'ACTIVE'),
    (3, 'legacy-courseflow', 'courseflow-identity', 'student@courseflow.local', 'student@courseflow.local', TRUE, 'ACTIVE')
ON CONFLICT (issuer, subject) DO UPDATE SET user_id = EXCLUDED.user_id, last_seen_at = NOW(), status = 'ACTIVE';

INSERT INTO external_identity_links (user_id, provider, issuer, subject, email_at_link, email_verified_at_link, status)
SELECT seed.user_id, 'keycloak', issuer.value, seed.subject, seed.email, TRUE, 'ACTIVE'
FROM (VALUES
    (1, '11111111-1111-4111-8111-111111111111', 'admin@courseflow.local'),
    (2, '22222222-2222-4222-8222-222222222222', 'instructor@courseflow.local'),
    (3, '33333333-3333-4333-8333-333333333333', 'student@courseflow.local')
) AS seed(user_id, subject, email)
CROSS JOIN (VALUES
    ('http://localhost:18080/realms/courseflow'),
    ('http://keycloak:8080/realms/courseflow')
) AS issuer(value)
ON CONFLICT (issuer, subject) DO UPDATE SET
    user_id = EXCLUDED.user_id,
    email_at_link = EXCLUDED.email_at_link,
    email_verified_at_link = EXCLUDED.email_verified_at_link,
    last_seen_at = NOW(),
    status = 'ACTIVE';

INSERT INTO user_role_assignments (user_id, role_id, scope_type, granted_by)
SELECT seed.user_id, r.id, 'PLATFORM', 'demo'
FROM (VALUES
    (1, 'ADMIN'),
    (2, 'INSTRUCTOR'),
    (3, 'STUDENT')
) AS seed(user_id, role_code)
JOIN roles r ON r.code = seed.role_code
ON CONFLICT (user_id, role_id, scope_type, COALESCE(scope_id, '')) WHERE revoked_at IS NULL DO NOTHING;
