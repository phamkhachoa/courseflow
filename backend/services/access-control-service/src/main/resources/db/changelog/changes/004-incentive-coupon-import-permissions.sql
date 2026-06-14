-- liquibase formatted sql
-- changeset courseflow:access-control-004-incentive-coupon-import-permissions splitStatements:false

UPDATE permissions
SET description = 'Manage individual coupons and coupon lifecycle operations',
    category = 'incentive',
    scope_type = 'APPLICATION'
WHERE code = 'incentive:coupon:manage';

INSERT INTO permissions (code, description, category, scope_type) VALUES
    ('incentive:coupon:read',
     'Read coupon catalog, masked coupon views and coupon operational metadata',
     'incentive',
     'APPLICATION'),
    ('incentive:coupon:import:read',
     'Read coupon import dry-run, approval, operation history and masked exports',
     'incentive',
     'APPLICATION'),
    ('incentive:coupon:import:manage',
     'Run coupon import dry-runs, request approvals and commit approved imports',
     'incentive',
     'APPLICATION'),
    ('incentive:coupon:import:review',
     'Review, approve and reject coupon import approvals',
     'incentive',
     'APPLICATION')
ON CONFLICT (code) DO UPDATE
SET description = EXCLUDED.description,
    category = EXCLUDED.category,
    scope_type = EXCLUDED.scope_type;

DELETE FROM role_permission_grants grants
USING roles role
WHERE grants.role_id = role.id
  AND role.code = 'INCENTIVE_OPERATOR'
  AND grants.permission_code = 'incentive:coupon:manage';

INSERT INTO role_permission_grants (role_id, permission_code, effect)
SELECT role.id, seed.permission_code, 'ALLOW'
FROM (VALUES
    ('INCENTIVE_ADMIN',    'incentive:coupon:read'),
    ('INCENTIVE_ADMIN',    'incentive:coupon:manage'),
    ('INCENTIVE_ADMIN',    'incentive:coupon:import:read'),
    ('INCENTIVE_ADMIN',    'incentive:coupon:import:manage'),
    ('INCENTIVE_ADMIN',    'incentive:coupon:import:review'),
    ('INCENTIVE_REVIEWER', 'incentive:coupon:read'),
    ('INCENTIVE_REVIEWER', 'incentive:coupon:import:read'),
    ('INCENTIVE_REVIEWER', 'incentive:coupon:import:review'),
    ('INCENTIVE_OPERATOR', 'incentive:coupon:read'),
    ('INCENTIVE_OPERATOR', 'incentive:coupon:import:read'),
    ('INCENTIVE_OPERATOR', 'incentive:coupon:import:manage')
) AS seed(role_code, permission_code)
JOIN roles role ON role.code = seed.role_code
ON CONFLICT (role_id, permission_code) DO UPDATE
SET effect = EXCLUDED.effect;
