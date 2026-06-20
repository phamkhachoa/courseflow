# Catalog Runtime Operations Gate

`catalog_runtime_ops_report.v1` is the production-like gate for Iceberg catalog runtime readiness.
It is intentionally separate from local Trino/Iceberg/MinIO smoke tests.

## Purpose

Local smokes prove table creation, cross-engine read/append and stale commit rejection in the
developer stack. They do not prove that the enterprise catalog service can survive a staging or
production failure.

This gate closes only these catalog runtime gaps when strict-passing:

- `production_catalog_ha`
- `production_catalog_concurrency_locking`
- `managed_catalog_failover`
- `multi_az_catalog_deployment`
- `production_catalog_backup_restore_pitr`

It does not close platform runtime IaC, DataHub/OpenMetadata catalog lineage, semantic serving,
source onboarding, schema registry, security, orchestration or secret-management blockers.

## Evidence Contract

Run:

```bash
enterprise-dp catalog-runtime-ops-report \
  --root dp \
  --environment staging \
  --evidence evidence/managed-catalog-runtime-evidence.json \
  --output build/catalog-runtime-ops/catalog-runtime-ops.json
```

The evidence file must be a real staging/prod export or external attestation with:

- `artifact_type=managed_catalog_runtime_evidence.v1`
- `environment` matching the report target
- `evidence_source` equal to `ci_tool_output` or `external_attestation`
- `production_evidence=true`, `sample=false`, `redacted=true`
- release id and change ticket hash-bound in `binding`
- catalog provider, endpoint, warehouse URI, service identity and catalog hash
- replica count >= 2 and availability zones >= 2
- failover tested and read/write after failover passed
- optimistic locking, concurrent commit probe, stale commit rejection and lost-update prevention
- backup enabled, PITR enabled and restore test passed
- audit sink hash, non-zero event count and zero failed events
- external attestation with verified signature and subject hash match
- upstream evidence hashes bound to the report

## Review Behavior

The production review pack accepts a staging/prod `catalog_runtime_ops_report.v1` only when
`readiness_state=production_like_ready`, `mode=runtime_attested`, `passed=true` and every strict
check above passes.

A local report is review-only and cannot close production catalog runtime gaps. A staging report
attached to a prod review also fails closed.
