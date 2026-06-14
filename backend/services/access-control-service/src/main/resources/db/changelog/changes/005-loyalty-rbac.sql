-- liquibase formatted sql
-- changeset courseflow:access-control-005-loyalty-rbac splitStatements:false

INSERT INTO permissions (code, description, category, scope_type) VALUES
    ('loyalty:read',                'Read loyalty programs, accounts, ledgers, and operational views', 'loyalty', 'TENANT'),
    ('loyalty:program:write',       'Create and manage loyalty programs and client bindings',          'loyalty', 'APPLICATION'),
    ('loyalty:ledger:adjust',       'Create manual loyalty point adjustments',                         'loyalty', 'APPLICATION'),
    ('loyalty:ledger:reverse',      'Reverse immutable loyalty point ledger entries',                   'loyalty', 'APPLICATION'),
    ('loyalty:expiry:read',         'Run and inspect loyalty point expiry dry-runs',                    'loyalty', 'APPLICATION'),
    ('loyalty:expiry:execute',      'Execute approved loyalty point expiry batches',                    'loyalty', 'APPLICATION'),
    ('loyalty:audit:read',          'Read loyalty audit and timeline records',                          'loyalty', 'APPLICATION'),
    ('loyalty:reconciliation:read', 'Read loyalty reconciliation and balance evidence',                 'loyalty', 'APPLICATION'),
    ('loyalty:runtime:operate',     'Operate trusted loyalty runtime integrations',                     'loyalty', 'APPLICATION')
ON CONFLICT (code) DO UPDATE
SET description = EXCLUDED.description,
    category = EXCLUDED.category,
    scope_type = EXCLUDED.scope_type;

INSERT INTO roles (id, code, name, description, is_system, is_operator, rank, parent_role_id, created_by, updated_by) VALUES
    ('10000000-0000-4000-8000-000000000111', 'LOYALTY_ADMIN',
     'Loyalty administrator', 'Manages loyalty programs, account operations, ledger corrections, expiry, audit and reconciliation.', TRUE, TRUE, 75, NULL, 'migration', 'migration'),
    ('10000000-0000-4000-8000-000000000112', 'LOYALTY_REVIEWER',
     'Loyalty reviewer', 'Reviews loyalty operational evidence, expiry plans, audit trails and reconciliation views.', TRUE, TRUE, 70, NULL, 'migration', 'migration'),
    ('10000000-0000-4000-8000-000000000113', 'LOYALTY_OPERATOR',
     'Loyalty operator', 'Runs support adjustments, reversals, dry-runs and reconciliation operations for loyalty accounts.', TRUE, TRUE, 65, NULL, 'migration', 'migration')
ON CONFLICT (code) DO NOTHING;

INSERT INTO role_permission_grants (role_id, permission_code, effect)
SELECT role.id, seed.permission_code, 'ALLOW'
FROM (VALUES
    ('LOYALTY_ADMIN',    'loyalty:read'),
    ('LOYALTY_ADMIN',    'loyalty:program:write'),
    ('LOYALTY_ADMIN',    'loyalty:ledger:adjust'),
    ('LOYALTY_ADMIN',    'loyalty:ledger:reverse'),
    ('LOYALTY_ADMIN',    'loyalty:expiry:read'),
    ('LOYALTY_ADMIN',    'loyalty:expiry:execute'),
    ('LOYALTY_ADMIN',    'loyalty:audit:read'),
    ('LOYALTY_ADMIN',    'loyalty:reconciliation:read'),
    ('LOYALTY_ADMIN',    'loyalty:runtime:operate'),
    ('LOYALTY_REVIEWER', 'loyalty:read'),
    ('LOYALTY_REVIEWER', 'loyalty:expiry:read'),
    ('LOYALTY_REVIEWER', 'loyalty:audit:read'),
    ('LOYALTY_REVIEWER', 'loyalty:reconciliation:read'),
    ('LOYALTY_OPERATOR', 'loyalty:read'),
    ('LOYALTY_OPERATOR', 'loyalty:ledger:adjust'),
    ('LOYALTY_OPERATOR', 'loyalty:ledger:reverse'),
    ('LOYALTY_OPERATOR', 'loyalty:expiry:read'),
    ('LOYALTY_OPERATOR', 'loyalty:audit:read'),
    ('LOYALTY_OPERATOR', 'loyalty:reconciliation:read'),
    ('LOYALTY_OPERATOR', 'loyalty:runtime:operate')
) AS seed(role_code, permission_code)
JOIN roles role ON role.code = seed.role_code
ON CONFLICT (role_id, permission_code) DO UPDATE
SET effect = EXCLUDED.effect;
