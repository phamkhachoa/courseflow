# Source-To-Bronze Production Readiness

`enterprise-dp source-readiness-check` creates `source_readiness_report.v1`, the production-readiness
gate for a registered source before it is allowed to feed approved Bronze tables.

`enterprise-dp source-readiness-bundle` is the operator path for assembling the full evidence pack.
It runs bridge normalization when required, first Bronze ingestion, replay, schema compatibility,
offset ledger, catalog, OpenLineage and the final readiness report into one reviewable directory.

`governance/source-activations.yaml` is the activation ledger. A source readiness report or bundle can
pass without rewriting the static source registry from `pilot` to `production_ready`; the approved
activation record binds the readiness id, evidence hashes, source registry hash, change request,
environment, expiry and gate badges. Portfolio readiness treats a source as production-ready only
when the activation is active, current, environment-compatible and not superseded by a newer revoked
or failed record.

`enterprise-dp source-activate` is the reviewed promotion step. It reads a passed
`source_readiness_bundle.v1`, re-hashes the bundle, readiness report and source registry from disk,
checks maker-checker/change-request alignment, requires a passing `runtime_readiness_report.v1` for
staging/prod, and appends the activation ledger only when all activation gates pass.

`enterprise-dp source-revoke` is the reviewed safety stop. It appends a newer `revoked` event to the
same ledger and writes a revoked active-pointer tombstone. It does not edit historical activation
records; portfolio readiness sees the newer revoked event and returns the source to blocked.

`enterprise-dp source-activation-ops-report` is the day-2 operations view. It audits the activation
ledger, active pointers, expiry windows, source-registry hash drift and revoked/expired states so
operators can renew, repair or revoke sources before P0 use cases lose trusted inputs.
For staging/prod it is intentionally fail-closed: any P0 source that is unactivated, non-active,
expired/revoked, missing a valid active pointer, missing runtime readiness evidence or drifting from
the current source-registry hash makes the report `passed=false`. A static
`status: production_ready` in the source registry is only desired state; runtime activation still
requires the ledger record, active pointer and evidence hashes.

`enterprise-dp production-review-pack` can attach the resulting `source_activation_ops_report.v1`
with `--source-activation-ops-report`. It removes the P0 `source-onboarding` blocker only for a
staging/prod report with `mode=runtime_attested`, `readiness_state=production_like_ready`, every
registered P0 source active and production-ready, valid runtime-readiness evidence, valid active
pointers and zero registry drift/runtime/pointer issues. Local source activation preflight reports
remain useful for operators but do not remove the production blocker.

The check is group-wide. Every product source uses the same gate whether it comes from commerce, CRM,
HRIS, ERP, support, risk or any other future platform. The first non-pilot proof source is
`enterprise-commerce-benefit-settled-outbox`.

## Evidence Pack

A production-like readiness check should attach:

- `platform/ingestion/source-registry.yaml` entry for source ownership, raw source, canonical topic,
  Bronze target, bridge, privacy and evidence requirements.
- Bridge manifest from `enterprise-dp source-bridge-normalize` when `bridge.required=true`; the
  manifest must prove the approved normalizer, source id, canonical topic, output hash and preserved
  source positions.
- Bronze ingestion manifest from `enterprise-dp ingest-bronze`.
- Replay manifest from the same source range proving zero additional approved Bronze rows.
- Source offset ledger from `enterprise-dp offset-ledger-record`, including partition watermarks,
  record hash bindings and Iceberg snapshot metadata.
- Schema registry compatibility report from `enterprise-dp schema-registry-check`.
- Change-control evidence from `enterprise-dp change-control-check`.
- Catalog bundle from `enterprise-dp catalog-export`.
- OpenLineage events from `enterprise-dp openlineage-export`.
- Approved activation entry in `governance/source-activations.yaml` when the source should count as
  effectively production-ready in portfolio readiness.

Production-like direct-canonical example:

```bash
enterprise-dp source-readiness-check \
  --root dp \
  --source-id enterprise-commerce-benefit-settled-outbox \
  --environment staging \
  --ingestion-manifest build/bronze/manifests/events_benefit_settled.first.json \
  --replay-manifest build/bronze/manifests/events_benefit_settled.replay.json \
  --offset-ledger build/offset-ledger/finance-benefit-settled.json \
  --schema-registry-report build/schema/finance-benefit-settled.json \
  --change-control-evidence build/change-control/source-onboarding.json \
  --catalog-bundle build/catalog/catalog-bundle.json \
  --openlineage-events build/lineage/openlineage.jsonl \
  --output build/readiness/source-readiness.json
```

Bridge-required local preflight example:

```bash
enterprise-dp source-readiness-check \
  --root dp \
  --source-id <registered-source-id> \
  --environment local \
  --bridge-manifest build/source-bridge/manifests/<registered-source-id>.local.json \
  --ingestion-manifest build/bronze/manifests/<bronze-target>.first.json \
  --replay-manifest build/bronze/manifests/<bronze-target>.replay.json \
  --schema-registry-report build/schema/<canonical-topic>.json \
  --output build/readiness/source-readiness.local.json
```

End-to-end bundle example:

```bash
enterprise-dp source-readiness-bundle \
  --root dp \
  --source-id <registered-source-id> \
  --input samples/<domain>/<source>.jsonl \
  --output-dir build/source-readiness/<registered-source-id> \
  --environment staging \
  --schema-registry-uri https://schema-registry.staging.example \
  --change-request-id <approved-source-onboarding-change> \
  --target-snapshot-id <iceberg-snapshot-id> \
  --table-metadata-uri <iceberg-metadata-uri> \
  --table-metadata-hash <sha256:metadata-hash>
```

Activation example:

```bash
enterprise-dp source-activate \
  --root dp \
  --bundle build/source-readiness/<registered-source-id>/summary/<registered-source-id>.source-readiness-bundle.json \
  --output build/source-readiness/<registered-source-id>/activation/source-activation.json \
  --requested-by <source-owner> \
  --approved-by <data-platform-approver> \
  --change-request-id <approved-source-onboarding-change> \
  --runtime-readiness-report build/runtime/staging-readiness.json \
  --ledger governance/source-activations.yaml \
  --expires-at 2026-07-18T11:00:00Z
```

Revocation example:

```bash
enterprise-dp source-revoke \
  --root dp \
  --source-id <registered-source-id> \
  --environment staging \
  --output build/source-readiness/<registered-source-id>/revocation/source-revocation.json \
  --requested-by <source-owner> \
  --approved-by <data-platform-approver> \
  --change-request-id <approved-source-activation-revoke-change> \
  --ledger governance/source-activations.yaml \
  --reason "Evidence is stale or source registry drift was detected." \
  --evidence-uri evidence://source-activations/<registered-source-id>/staging/revocation-analysis.json
```

Operations report example:

```bash
enterprise-dp source-activation-ops-report \
  --root dp \
  --output build/source-activation-ops/staging.json \
  --environment staging \
  --ledger governance/source-activations.yaml \
  --active-pointer-dir governance/source-active-pointers \
  --expiring-within-days 30
```

Production review gate example:

```bash
enterprise-dp production-review-pack \
  --root dp \
  --output-dir build/production-review-pack \
  --environment staging \
  --source-activation-ops-report build/source-activation-ops/staging.json
```

Portfolio overlay example:

```bash
enterprise-dp portfolio-readiness-report \
  --root dp \
  --output build/portfolio/readiness.json \
  --environment staging \
  --source-activation-ledger governance/source-activations.yaml
```

## Blocking Gates

The report blocks readiness when:

- The source is not registered or still has an unsupported status.
- The bridge or normalizer is not ready for production-like environments.
- A bridge-required source does not attach a bridge manifest, or the bridge output hash does not
  match the Bronze ingestion input hash.
- Source position is not preserved.
- Schema compatibility fails or the required subject is missing.
- Production-like reports only use local schema registry evidence.
- Bronze ingestion has quarantined rows, missing source offsets or missing content hashes.
- Replay adds new approved rows or changes source position coverage.
- Source offset ledger is missing, failed, does not bind to the same ingestion run, has offset gaps
  or lacks Iceberg snapshot metadata.
- Change-control evidence is missing, failed or not for source onboarding.
- Catalog or OpenLineage evidence does not prove topic-to-Bronze lineage.
- Staging/prod activation does not attach a passing runtime readiness report, or the runtime report
  environment does not match the source activation environment.

## Next Hardening

Production runtime should persist the source offset ledger to an append-only metadata store and attach
broker ACL/lag reports, sink commit evidence and quarantine triage links before the group treats the
source as fully live.
