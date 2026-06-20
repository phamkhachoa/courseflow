# Product Readiness Freshness Incident Response

This runbook covers Product Readiness Freshness incidents exported by
`platform/governance/reports/product-readiness-freshness-incident-export-v1.yaml`.

## Scope

Use this runbook for these tenant-safe incident conditions:

- `product_readiness_freshness_report_missing`
- `product_readiness_freshness_report_stale`
- `product_readiness_runtime_route_unreachable`
- `product_readiness_static_snapshot_stale`
- `product_readiness_runtime_error_or_audit_failure`
- `product_readiness_runtime_audit_gap`

Do not copy raw tenant IDs, principal IDs, request bodies, credential values, service tokens
or raw runtime payloads into incident notes. Use the exported incident ID and
`product-readiness:<hash>` ref.

## Steps

1. Detect the open incident in the Product Readiness Freshness incident export.
2. Acknowledge the incident in the Admin/Ops dashboard using the exported incident ID.
3. Assign Admin/Ops owner plus SA AI Platform/Engineer support using role aliases.
4. Contain product readiness sign-off until freshness, route health and audit coverage recover.
5. Remediate by refreshing snapshots, restoring the route or repairing audit coverage.
6. Verify by re-running freshness and incident exports until open product incidents clear.
7. Communicate product readiness impact without raw tenant, service or credential identifiers.
8. Close or downgrade only after evidence refs show recovered product readiness freshness.

## Evidence

- Structured runbook spec: `platform/operations/runbooks/product-readiness-freshness-incident-response-v1.yaml`
- Drill report: `platform/operations/reports/product-readiness-freshness-incident-response-drill-v1.yaml`
- Incident export: `platform/governance/reports/product-readiness-freshness-incident-export-v1.yaml`
- Freshness report: `platform/product/reports/ai-platform-product-readiness-freshness-v1.yaml`
