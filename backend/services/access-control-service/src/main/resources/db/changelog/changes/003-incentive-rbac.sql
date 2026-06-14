-- liquibase formatted sql
-- changeset courseflow:access-control-003-incentive-rbac splitStatements:false

ALTER TABLE permissions DROP CONSTRAINT IF EXISTS permissions_scope_type_check;
ALTER TABLE permissions ADD CONSTRAINT permissions_scope_type_check
    CHECK (scope_type IN ('ANY','PLATFORM','TENANT','APPLICATION','ORG','COURSE','DEPARTMENT','SECTION'));

ALTER TABLE user_role_assignments DROP CONSTRAINT IF EXISTS user_role_assignments_scope_type_check;
ALTER TABLE user_role_assignments ADD CONSTRAINT user_role_assignments_scope_type_check
    CHECK (scope_type IN ('PLATFORM','TENANT','APPLICATION','ORG','COURSE','DEPARTMENT','SECTION'));

UPDATE permissions
SET scope_type = 'ANY',
    description = 'Assign or revoke product roles across CourseFlow bounded contexts'
WHERE code = 'user:assign-role';

INSERT INTO permissions (code, description, category, scope_type) VALUES
    ('incentive:read',                'Read incentive platform configuration and operational views', 'incentive', 'TENANT'),
    ('incentive:campaign:write',      'Create and edit incentive campaigns and versions',            'incentive', 'APPLICATION'),
    ('incentive:campaign:review',     'Review and approve incentive campaign versions',              'incentive', 'APPLICATION'),
    ('incentive:coupon:manage',       'Manage coupons and coupon import operations',                 'incentive', 'APPLICATION'),
    ('incentive:audit:read',          'Read incentive audit and timeline records',                   'incentive', 'APPLICATION'),
    ('incentive:reconciliation:read', 'Read incentive reconciliation projections',                   'incentive', 'APPLICATION'),
    ('incentive:runtime:operate',     'Operate trusted incentive runtime integrations',              'incentive', 'APPLICATION')
ON CONFLICT (code) DO UPDATE
SET description = EXCLUDED.description,
    category = EXCLUDED.category,
    scope_type = EXCLUDED.scope_type;

INSERT INTO roles (id, code, name, description, is_system, is_operator, rank, parent_role_id, created_by, updated_by) VALUES
    ('10000000-0000-4000-8000-000000000101', 'INCENTIVE_ADMIN',
     'Incentive administrator', 'Manages generic incentive applications, campaigns, coupons, audit and reconciliation.', TRUE, TRUE, 75, NULL, 'migration', 'migration'),
    ('10000000-0000-4000-8000-000000000102', 'INCENTIVE_REVIEWER',
     'Incentive reviewer', 'Reviews incentive campaign and coupon import changes before publish or execution.', TRUE, TRUE, 70, NULL, 'migration', 'migration'),
    ('10000000-0000-4000-8000-000000000103', 'INCENTIVE_OPERATOR',
     'Incentive operator', 'Runs support and reconciliation operations for trusted incentive integrations.', TRUE, TRUE, 65, NULL, 'migration', 'migration')
ON CONFLICT (code) DO NOTHING;

INSERT INTO role_permission_grants (role_id, permission_code, effect)
SELECT r.id, seed.permission_code, 'ALLOW'
FROM (VALUES
    ('INCENTIVE_ADMIN',    'incentive:read'),
    ('INCENTIVE_ADMIN',    'incentive:campaign:write'),
    ('INCENTIVE_ADMIN',    'incentive:campaign:review'),
    ('INCENTIVE_ADMIN',    'incentive:coupon:manage'),
    ('INCENTIVE_ADMIN',    'incentive:audit:read'),
    ('INCENTIVE_ADMIN',    'incentive:reconciliation:read'),
    ('INCENTIVE_ADMIN',    'incentive:runtime:operate'),
    ('INCENTIVE_REVIEWER', 'incentive:read'),
    ('INCENTIVE_REVIEWER', 'incentive:campaign:review'),
    ('INCENTIVE_REVIEWER', 'incentive:audit:read'),
    ('INCENTIVE_OPERATOR', 'incentive:read'),
    ('INCENTIVE_OPERATOR', 'incentive:coupon:manage'),
    ('INCENTIVE_OPERATOR', 'incentive:audit:read'),
    ('INCENTIVE_OPERATOR', 'incentive:reconciliation:read'),
    ('INCENTIVE_OPERATOR', 'incentive:runtime:operate')
) AS seed(role_code, permission_code)
JOIN roles r ON r.code = seed.role_code
ON CONFLICT (role_id, permission_code) DO NOTHING;
