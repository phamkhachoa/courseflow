# Data Product Control Tower

`platform/control-tower/` defines the P0 operating view for enterprise data product health. It is
owned by the data platform team and consumed by domain owners, governance, security, enterprise
reporting and approved BI/ML consumers.

## Purpose

The Control Tower is an evidence aggregator and decision report. It does not replace lower-level
validators. It reads contracts, catalog metadata, lineage, quality profiles, release evidence,
access governance, access grant operations, source activation operations, event/CDC ingestion
runtime, Bronze lakehouse operations, Silver/Gold publication operations, Quality/SLO release gate
operations, semantic metric serving operations, schema registry operations, contract impact reports,
data-plane smoke reports, runtime readiness and capability maturity reports, then surfaces which data
products can or cannot move toward production signoff.

The local materialization runner `control_tower.materialize_gold.from_report.v1` turns that decision
report into four dashboard-ready Gold JSONL outputs:

- `gold.data_product_inventory`
- `gold.contract_compliance_daily`
- `gold.quality_sla_daily`
- `gold.lineage_coverage_daily`

## Required Views

| View | Decision |
|---|---|
| Executive health overview | Which domains/products are blocked and why. |
| Data product inventory | Owner, steward, lifecycle, classification, SLO and readiness per data product. |
| Contract compliance | Contract validity, lifecycle state, schema/quality/access/retention coverage. |
| Quality and SLA board | Freshness, release evidence, runtime lineage and blocking quality state. |
| Lineage coverage | Static catalog lineage and runtime run evidence per data product. |
| Catalog lineage operations board | Catalog publish status, OpenLineage event count, publish receipt and lineage coverage gaps. |
| Access/privacy board | Policy, consumer contract and grant evidence coverage. |
| Access operations board | Registry-wide grant P0 issues, overdue review queue and expiry warnings. |
| Source activation operations board | Ledger validity, active-pointer consistency, P0 source activation gaps and registry drift. |
| Event/CDC ingestion runtime board | Connector health, lag, DLT, backpressure and offset-ledger evidence for active sources. |
| Bronze lakehouse operations board | Offset ledgers, replay proof, Iceberg commit metadata and maintenance evidence for Bronze tables. |
| Silver/Gold publication operations board | Release evidence, promotion, activation, active pointer and rollback readiness for serving data products. |
| Quality/SLO release gate operations board | Quality profile coverage, release quality/freshness gates, runtime quality evidence, freshness SLO state, alert evidence and incident/SLO status. |
| Semantic metric serving operations board | Metric certification, semantic view manifest, deployment smoke-test evidence and BI/app usage tracking. |
| Schema registry operations board | Topic compatibility, publication evidence, producer schema-id enforcement, broker/sink validation and signed external attestation. |
| Data-plane smoke board | Attached source -> Bronze -> Silver/Gold -> catalog -> release evidence -> query probe result for the first executable slice. |
| Contract impact board | Blocked schema/topic changes, review-required changes and affected use cases. |
| Runtime readiness board | Runtime/IaC/service-health/backup/DR readiness for the target environment. |
| Capability maturity | P0 platform capability current level vs target level. |

## P0 Blocking Rules

- Data product contract validation fails.
- Gold data product is not `ACTIVE`.
- Gold data product lacks quality profile coverage.
- Required catalog or runtime lineage is missing.
- Catalog lineage operations report has an invalid artifact type, environment mismatch, wrong
  readiness state, catalog hash drift, failed publish manifest, invalid OpenLineage JSONL, local
  production namespace/producer, missing publish receipt or product lineage gaps.
- Silver/Gold serving data product fails access policy or consumer contract checks.
- Silver/Gold serving data product has P0 access-grant operations issues.
- Source activation operations report has an invalid/missing ledger, environment mismatch, registry
  drift, expired/revoked activation, active-pointer issue or unactivated P0 source.
- Event/CDC ingestion runtime report has an invalid artifact type, environment mismatch, wrong
  readiness state, stale/synthetic/missing production evidence, connector failures, lag over SLO,
  DLT backlog, backpressure or missing offset ledger evidence for P0 sources.
- Bronze lakehouse operations report has an invalid artifact type, environment mismatch, wrong
  readiness state, missing/failed offset ledger, missing replay proof, failed Iceberg commit
  evidence, quarantine breach, append-only drift or failing maintenance evidence for P0 Bronze
  tables.
- Silver/Gold publication operations report has an invalid artifact type, environment mismatch,
  wrong readiness state, missing release evidence, failed promotion/activation, missing or drifting
  active pointer, missing rollback target or missing production change ticket.
- Quality/SLO release gates operations report has an invalid artifact type, environment mismatch,
  wrong readiness state, missing release/runtime/alert evidence, failed release quality/freshness
  gates, stale freshness, failing runtime quality, open P0 incident, breached SLA or product-level
  quality/SLO issue.
- Semantic metric serving operations report has an invalid artifact type, environment mismatch,
  wrong readiness state, invalid registry, missing/failed metric certification, invalid manifest,
  registry hash drift, uncertified production metric, missing/failed deployment evidence, failed
  smoke/access check, missing usage evidence or disabled usage tracking.
- Schema registry operations report has an invalid artifact type, environment mismatch, wrong
  readiness state, failed compatibility report, missing publication evidence, missing/invalid signed
  external attestation, subject registration gap, missing schema id, compatibility mode mismatch,
  payload hash drift, producer enforcement gap or missing broker/sink validation.
- Attached data-plane smoke report has an invalid artifact type, environment mismatch, failed
  release evidence, missing/mismatched layer hashes or row counts, failed layer quality or failed
  Gold query probe.
- Attached contract impact report blocks a topic/schema change.
- Runtime readiness report for the target environment is not passing.
- Gold data product has no passing release evidence.
- P0 platform capabilities are still below target maturity.

`enterprise-dp control-tower-report` intentionally exits non-zero while these blockers exist. This is
the expected production signoff behavior.

## Local Flow

```bash
enterprise-dp control-tower-report \
  --root . \
  --output build/control-tower/report.json \
  --catalog-lineage-ops-report build/evidence/catalog-lineage-ops-prod.json \
  --access-grant-ops-report build/evidence/access-grant-ops.json \
  --source-activation-ops-report build/evidence/source-activation-ops-staging.json \
  --ingestion-runtime-report build/evidence/event-cdc-ingestion-runtime-prod.json \
  --bronze-lakehouse-ops-report build/evidence/bronze-lakehouse-ops-prod.json \
  --silver-gold-publication-ops-report build/evidence/silver-gold-publication-ops-prod.json \
  --quality-slo-release-gates-ops-report build/evidence/quality-slo-release-gates-ops-prod.json \
  --semantic-metric-serving-ops-report build/evidence/semantic-metric-serving-ops-prod.json \
  --schema-registry-ops-report build/evidence/schema-registry-ops-prod.json \
  --data-plane-smoke-report build/data-plane-smoke/data-plane-smoke-report.json \
  --contract-impact-report build/evidence/contract-impact-billing.json \
  --runtime-readiness-report build/evidence/runtime-readiness-prod.json

enterprise-dp run-use-case \
  --root . \
  --use-case data-product-control-tower \
  --input build/control-tower/report.json \
  --output-dir build/control-tower/run \
  --release-id local-control-tower \
  --environment local
```

For partner review, prefer the packaged command:

```bash
make production-review-pack
```

It writes `production_review_pack.v1` with artifact hashes, the data-plane smoke status, Control
Tower blocker counts and the P0 gap backlog. For the stronger partner-review path, first attach
multi-use-case release evidence:

```bash
make portfolio-release-smoke
make production-review-pack PORTFOLIO_RELEASE_SMOKE_REPORT=build/portfolio-release-smoke/portfolio-release-smoke-report.json
```

With the current local portfolio evidence, this path proves the implemented runners can cover the
current Gold portfolio, attaches local source activation operations evidence for P0 sources and
keeps non-infrastructure Control Tower blockers at zero. Remaining blockers should be treated as
live-runtime/capability maturity gaps, not hidden data-product defects. If `make event-backbone-smoke`
has been run on a Docker-enabled machine, attach it too:

```bash
make production-review-pack \
  PORTFOLIO_RELEASE_SMOKE_REPORT=build/portfolio-release-smoke/portfolio-release-smoke-report.json \
  EVENT_BACKBONE_SMOKE_REPORT=build/event-backbone-smoke/event-backbone-smoke-report.json
```

The correct external review wording is: Control Tower and DP artifact model are ready for partner
review; production signoff remains false until live Kafka/Redpanda, Iceberg, query runtime,
orchestration, runtime security enforcement and P0 capability evidence are attached.
