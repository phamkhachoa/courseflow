# Bronze Lakehouse Operations Gate

`bronze_lakehouse_ops_report.v1` is the P0 operations gate for immutable Bronze tables. It proves
that source records landed in Iceberg with offset-ledger binding, replay evidence, append-only
controls and maintenance evidence.

## Decision

`enterprise-dp bronze-lakehouse-ops-report` reads registered sources from
`platform/ingestion/source-registry.yaml`, attached `source_offset_ledger.v1` artifacts and optional
`bronze_lakehouse_maintenance_evidence.v1`. Local environments may pass as a preflight without
runtime evidence. Staging and production must attach non-synthetic ledgers and maintenance evidence
for P0 sources.

Control Tower consumes the report through `--bronze-lakehouse-ops-report` and blocks production
signoff when the artifact is missing, from the wrong environment, not `production_like_ready`, or
when any P0 Bronze table has ledger, commit or maintenance failures.

## Evidence Contract

`source_offset_ledger.v1` must prove:

- Source id, environment, canonical topic and Bronze target match the registry.
- Commit status is `committed`.
- Table format is Iceberg.
- Production-like commits include target snapshot id, table metadata URI and metadata hash.
- Replay proof is attached.
- Quarantine count is zero unless an explicit policy allows otherwise.
- Source watermarks and record hash bindings are present.

`bronze_lakehouse_maintenance_evidence.v1` must include one row per P0 Bronze table:

| Field | Purpose |
|---|---|
| `append_only_enforced` | Proves Bronze writes cannot silently mutate raw history. |
| `compaction.status` | Proves small-file maintenance is passing or not required. |
| `snapshot_retention.status` | Proves snapshot retention keeps rollback/audit windows safe. |
| `orphan_cleanup.status` | Proves orphan cleanup is passing or not yet due. |
| `table_properties` | Proves Iceberg format v2 and commit/file-size properties are ready. |

## CLI

```bash
enterprise-dp bronze-lakehouse-ops-report \
  --root . \
  --environment prod \
  --offset-ledger build/evidence/billing-source-offset-ledger.json \
  --offset-ledger build/evidence/commerce-source-offset-ledger.json \
  --maintenance-evidence build/evidence/bronze-lakehouse-maintenance-prod.json \
  --output build/evidence/bronze-lakehouse-ops-prod.json
```

The command exits non-zero when global evidence checks fail or any P0 Bronze table fails. The report
exposes `decision_board.page_now` for missing ledgers, replay gaps, failed Iceberg commits,
append-only drift, compaction failures, snapshot-retention failures and orphan-cleanup failures.

## Current State

This repository now has the report contract, CLI, Control Tower gate and automated tests. It remains
below L2/L3 until a staging or production-like Iceberg sink emits live non-synthetic ledgers,
snapshot metadata and maintenance evidence from the actual lakehouse runtime.
