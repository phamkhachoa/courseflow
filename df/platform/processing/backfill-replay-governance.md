# Backfill And Replay Governance

Backfill and replay are production-impacting operations. They can change historical Silver/Gold
outputs, downstream metrics, ML training snapshots and finance or compliance reports. The platform
therefore treats backfill readiness as a governance decision layer, separate from data correctness
evidence.

## Artifact

`enterprise-df backfill-readiness-check` emits `backfill_readiness_report.v1`.

The report answers one question: is this bounded replay/backfill allowed to run or promote for the
target environment?

It does not replace:

- `source_offset_ledger.v1`, which proves Bronze source replay and committed watermarks.
- `lakehouse_snapshot_evidence.v1`, which proves Silver/Gold Iceberg snapshot correctness.
- `change_control_evidence.v1`, which proves maker-checker approval and rollback/impact controls.
- release promotion and activation manifests, which move a proven output into active serving.

## Required Scope

Every request in `governance/backfill-requests.yaml` must declare:

- Product, domain, use case, runner and primary output.
- Source ids, input snapshots or source offset ranges.
- Tenant scope and event-time window.
- Affected Silver/Gold data products.
- A run id, idempotency strategy, materialization strategy and concurrency lock.
- Expected row delta, maximum allowed row delta and affected partitions.
- Rollback strategy and previous active baseline when the output is already served.
- Active pointer URI/hash for the current served snapshot of the primary output.

Open-ended backfills are not production-ready. If the source range, tenant scope, partition scope or
event-time window is unclear, the readiness report must block execution.

## Production-Like Gates

Staging and production readiness require:

- Approved `backfill_replay` change-control evidence.
- Backfill plan URI/hash.
- Dry-run report URI/hash.
- Quality report URI/hash.
- Data-diff report URI/hash.
- Source offset ledger URI/hash.
- Lakehouse snapshot evidence URI/hash.
- Active pointer URI/hash proving the request baseline still matches the currently served snapshot.
- Release evidence URI/hash when the rebuilt output is promoted.
- Rollback plan, impact assessment and consumer communication plan.
- Maker-checker approvals including data steward and platform owner.

Production must additionally prove the staging report for the same request/scope when this moves
from staging validation to production replay.

## CLI Example

```bash
enterprise-df backfill-readiness-check \
  --root df \
  --request-id backfill_finance_benefit_reconciliation_staging \
  --environment staging \
  --backfill-plan build/backfill/plan.json \
  --dry-run-report build/backfill/dry-run.json \
  --quality-report build/backfill/quality.json \
  --data-diff-report build/backfill/data-diff.json \
  --source-offset-ledger build/ledger/source-offset-ledger.json \
  --snapshot-evidence build/snapshot/evidence.json \
  --active-state build/active/gold.finance_benefit_reconciliation.json \
  --change-control-evidence build/change-control/evidence.json \
  --output build/backfill/readiness.json
```

Exit code is `0` only when `passed=true`.
