# Production Data SLO and Release Gates

This spec defines the production gates for enterprise data platform P0 releases. It turns data
observability into a publish decision: a release or Gold activation cannot proceed unless the current
P0 signals are inside SLO and the evidence pack is attached to the change record.

## Scope

Gate semantics apply to every production-impacting data product, regardless of product or domain.
The currently onboarded P0 assets are implementation examples from the group data platform:

| Asset | Contract source | Production role |
|---|---|---|
| `recommendation.tracking.v1` | `contracts/topics/recommendation.tracking.v1.yaml` | P0 source topic for recommendation interaction tracking. |
| `bronze.events_recommendation_tracking` | `contracts/data-products/bronze.events_recommendation_tracking.v1.yaml` | Raw replayable event landing table. |
| `silver.learner_activity` | `contracts/data-products/silver.learner_activity.v1.yaml` | Pilot conformed activity table for the first onboarded product. |
| `gold.recsys_interactions` | `contracts/data-products/gold.recsys_interactions.v1.yaml` | ML and BI ready recommendation interaction snapshot. |
| `finance.benefit_settled.v1` | `contracts/topics/finance.benefit_settled.v1.yaml` | P0 source topic for finance benefit settlement reconciliation. |
| `bronze.events_benefit_settled` | `contracts/data-products/bronze.events_benefit_settled.v1.yaml` | Raw replayable finance settlement events. |
| `silver.finance_benefit_transactions` | `contracts/data-products/silver.finance_benefit_transactions.v1.yaml` | Normalized finance benefit transaction grain. |
| `gold.finance_benefit_reconciliation` | `contracts/data-products/gold.finance_benefit_reconciliation.v1.yaml` | Finance reconciliation evidence for paid orders, discounts, points, rewards and refunds. |

The SLO values below are sourced from each contract's `quality.freshnessSloMinutes`. This document
does not redefine contract semantics or compatibility rules.

Release evidence policy is defined as metadata-as-code in
`platform/observability/release-evidence-profiles.yaml`. Runnable use cases reference a
`releaseEvidenceProfile`; generic release evidence evaluates it through
`P0-RELEASE-EVIDENCE-PROFILE`.

Generic `run-use-case` releases enforce `P0-INGESTION-LAG` and `P0-FRESHNESS` from the ingestion and
pipeline manifests. Ingestion lag reads approved Bronze rows to compare `published_at` and
`ingested_at`; freshness compares the evaluation time with the latest Bronze ingestion time and
pipeline `generated_at` for Silver/Gold outputs.

## Gate Summary

| Gate ID | Signal | Production pass condition | Release action on fail |
|---|---|---|---|
| `P0-INGESTION-LAG` | Source event to Bronze landing lag for the candidate use-case input topic. | P99 `ingested_at - published_at` is `<= 15m` for the last closed 30 minute window, no active source partition is stalled for `> 15m`, and backlog is not increasing for two consecutive evaluations. | Block deploys that change ingestion, Bronze sinks, or downstream publication. Freeze impacted Gold publishes. |
| `P0-FRESHNESS` | Latest complete data product materialization age. | Bronze `<= 15m`, Silver `<= 60m`, Gold `<= 240m` in production, measured against the latest complete event-time partition or immutable snapshot. | Block downstream promotion for the stale layer and every dependent layer. |
| `P0-QUALITY` | Required quality checks, failed rows and quarantine state. | All required checks pass for the candidate window or snapshot. Any failed privacy, tenant isolation or `no_sensitive_payload` check is an automatic fail. Quarantined rows must be excluded from Gold and have a linked triage record. | Block publish. Open or attach incident if a P0 consumer is affected. |
| `P0-CONTRACT-COMPATIBILITY` | Topic schema and data product contract compatibility. | `cd df && make check` passes, schema registry compatibility for the topic is `BACKWARD_TRANSITIVE`, and data product changes preserve existing required fields, types, PII tags and access policy. | Reject release. Use a new major version or parallel asset for incompatible changes. |
| `P0-SCHEMA-REGISTRY-COMPATIBILITY` | Schema registry compatibility report. | Local report has `compatibility_passed=true`, or production provides a local `external_evidence_attestation.v1` for the durable external registry report. Raw external URI + hash alone is not sufficient. | Reject release until compatibility evidence is present, verifiable and passing. |
| `P0-ACCESS-POLICY` | Access-policy evidence report. | Local report has `passed=true`, or production provides a local `external_evidence_attestation.v1` for the durable external policy report. Raw external URI + hash alone is not sufficient. | Reject Gold activation until access-policy evidence is present, verifiable and passing. |
| `P0-PRODUCTION-EVIDENCE` | Required release evidence for production-like environments. | Staging/prod evidence includes code commit SHA, schema registry report URI and hash, validator output, access-policy check id, access-policy report URI and hash, access-grant evidence, retention evidence, lakehouse snapshot evidence and approver. | Reject production signoff until missing evidence is attached. |
| `P0-LAKEHOUSE-SNAPSHOT-EVIDENCE` | Iceberg commit evidence for Silver/Gold release candidates. | `lakehouse_snapshot_evidence.v1` exists and matches the release environment, pipeline manifest hash, primary output, Iceberg snapshot metadata, schema/partition hashes, row counts, content hash and upstream Bronze offset ledger. | Block staging/prod promotion and activation. |
| `P0-RELEASE-EVIDENCE-PROFILE` | Metadata-as-code release evidence policy. | The active release evidence profile applies to the use case and runner input kind, every required gate is present and passed, required artifacts and hashes exist, and local/prod evidence requirements are satisfied. | Reject the release until the evidence pack matches the active profile. |
| `P0-GOLD-EVIDENCE` | Audit evidence for the target Gold data-product activation. | Evidence pack exists before publish and ties snapshot id, table version, source offsets, contract version, code commit, quality report and lineage catalog record. | Do not activate or expose the Gold snapshot. Withdraw any snapshot that was exposed without evidence. |

## SLO Targets

Actual SLOs are loaded from each topic or data product contract. The table below shows the current
pilot asset values, not platform-wide constants.

| Asset | SLO | Measurement |
|---|---:|---|
| `recommendation.tracking.v1` ingestion to Bronze | 15 minutes | `ingested_at - published_at` by source service, topic and partition. |
| `bronze.events_recommendation_tracking` freshness | 15 minutes | `now() - max(ingested_at)` for the latest complete partition. |
| `silver.learner_activity` freshness | 60 minutes | `now() - max(materialized_at)` or the orchestrator materialization timestamp for the latest complete partition. |
| `gold.recsys_interactions` freshness | 240 minutes | `now() - max(built_at)` for the active immutable `dataset_snapshot_id`. |
| Required data quality checks | 100% pass | Every required check in the applicable topic or data product contract reports pass for the release window. |
| Contract compatibility | 100% pass | Local validator and external schema registry compatibility report both pass. |
| Gold publish evidence | 100% complete | Every activated Gold snapshot has a durable evidence record. |

## Required Observability Signals

Metric names may be adapted to the selected telemetry stack, but production must expose equivalent
signals with the labels shown here.

| Signal | Required labels | Notes |
|---|---|---|
| `enterprise_df_ingestion_lag_seconds` | `environment`, `product`, `topic`, `source_service`, `partition` | Event publish time to Bronze landing time. Emit p50, p95 and p99 or raw observations that can derive them. |
| `enterprise_df_source_backlog_records` | `environment`, `product`, `topic`, `partition` | Consumer backlog or unprocessed source records. |
| `enterprise_df_partition_stalled` | `environment`, `product`, `topic`, `partition` | Boolean gauge, `1` when the active source partition has not advanced inside its SLO. |
| `enterprise_df_data_product_freshness_seconds` | `environment`, `product`, `data_product`, `layer` | Latest complete materialization age. |
| `enterprise_df_quality_check_status` | `environment`, `product`, `data_product`, `check`, `severity` | Gauge, `1` pass and `0` fail. Required checks use `severity=blocking`. |
| `enterprise_df_quality_failed_rows` | `environment`, `product`, `data_product`, `check` | Failed row count for the evaluated window or snapshot. |
| `enterprise_df_quarantine_rows` | `environment`, `product`, `data_product`, `reason` | Quarantined rows excluded from publish. |
| `enterprise_df_contract_compatibility_status` | `environment`, `product`, `contract`, `compatibility_mode` | Gauge, `1` compatible and `0` incompatible. |
| `enterprise_df_gold_publish_evidence_status` | `environment`, `product`, `data_product` | Gauge, `1` only when the active Gold snapshot has a complete evidence pack. |
| `enterprise_df_release_gate_status` | `environment`, `product`, `domain`, `use_case`, `gate_id` | Gauge, `1` when the release evidence gate passed and `0` otherwise. |
| `enterprise_df_cost_attribution_rows_total` | `environment`, `product`, `domain`, `pipeline` | Row-count based proxy for product/domain/pipeline cost attribution until runtime cost collectors exist. |

High-cardinality values such as `dataset_snapshot_id`, source offset ranges and object table versions
belong in the evidence store and release record, not in high-frequency Prometheus labels.

## Evidence Pack

Every production release that changes P0 data platform behavior must attach an evidence pack. Gold
activation also requires a snapshot-specific evidence pack before any consumer reads the new snapshot.

Required fields:

| Field | Required for | Description |
|---|---|---|
| `release_id` | All P0 releases | Change, deploy or release identifier. |
| `environment` | All P0 releases | Must be `prod` for production signoff. |
| `release_evidence_profile_id` | All generic use-case releases | Active release evidence profile from `platform/observability/release-evidence-profiles.yaml`. |
| `release_evidence_profile_hash` | All generic use-case releases | Hash of the release evidence profile registry used to evaluate the release. |
| `code_commit_sha` | All P0 releases | Exact source revision used to build the release. |
| `contract_versions` | All P0 releases | Topic and data product contract versions evaluated. |
| `schema_registry_report_uri` | Contract changes | Compatibility report showing `BACKWARD_TRANSITIVE` pass for the topic. |
| `schema_registry_report_hash` | Contract changes | Hash of the schema compatibility report attached to the release. |
| `validator_output_uri` | All P0 releases | Stored output from `cd df && make check`. |
| `pipeline_run_id` | Pipeline changes and Gold publish | Orchestrator run that produced the candidate data. |
| `topic_offset_ranges` | Ingestion and Gold publish | Source topic, partition, start offset and end offset included in the release window. |
| `bronze_table_version` | Silver and Gold publish | Immutable Bronze table version or snapshot identifier. |
| `silver_table_version` | Gold publish | Immutable Silver table version or snapshot identifier. |
| `gold_dataset_snapshot_id` | Gold publish | Active immutable Gold snapshot id. |
| `quality_report_uri` | All P0 publishes | Machine-readable report for all required checks. |
| `freshness_report_uri` | All P0 publishes | Report proving the layer freshness SLOs. |
| `lineage_catalog_url` | Gold publish | Catalog lineage URL for the active snapshot. |
| `access_policy_check_id` | Gold publish | Evidence that row-level org isolation and PII policy were checked. |
| `access_policy_report_uri` | Gold publish | Access-policy report proving row-level isolation, persona allowlist, PII tags and audit metadata. |
| `access_policy_report_hash` | Gold publish | Hash of the access-policy report attached to the release. |
| `access_grant_evidence_uri` | Gold publish | Access-grant evidence proving approved grants, maker-checker approvals, expiry and runtime allow/deny decisions. |
| `access_grant_evidence_hash` | Gold publish | Hash of the access-grant evidence attached to the release. |
| `retention_evidence_uri` | Gold publish | Retention and erasure evidence proving policy match, expired-record scan, erasure replay and legal-hold checks. |
| `retention_evidence_hash` | Gold publish | Hash of the retention and erasure evidence attached to the release. |
| `approver` | Gold publish | Release owner or incident commander approving publication. |

External evidence stored outside the release workspace must be represented by a checked-in or
artifact-store-local attestation before a gate can pass:

```json
{
  "artifact_type": "external_evidence_attestation.v1",
  "evidence_kind": "schema_registry",
  "subject_uri": "s3://df-evidence/schema-registry/release-123.json",
  "subject_hash": "sha256:...",
  "environment": "prod",
  "release_id": "release-123",
  "producer": "schema-registry-workflow",
  "generated_at": "2026-01-15T10:10:10Z",
  "signature_algorithm": "Ed25519",
  "signing_key_id": "prod-ed25519-key-id",
  "signature": "base64:...",
  "passed": true
}
```

Supported `evidence_kind` values are `schema_registry`, `access_policy`, `access_grant` and
`retention_erasure`. The signature is computed over canonical JSON bytes of the attestation with
the `signature` field omitted, using `sort_keys=True`, compact separators and ASCII-safe encoding.
Release gates verify the signature against `platform/security/evidence-trust-keys.yaml`, and fail
closed for unknown, disabled, expired, wrong-environment, wrong-producer or wrong-evidence-kind
keys. The same verifier is available as `enterprise-df attestation-verify` for pre-release
operator checks. Retention attestations must additionally bind the signed payload to the release's
Gold data product, dataset snapshot id and content hash.

## Production Decision Flow

1. Validate contracts and project structure with `cd df && make check`.
2. Run schema registry compatibility for any topic or event schema change.
3. Execute the staging release gate against production-like data and save the evidence pack.
4. Before production deploy, re-check P0 ingestion lag and current freshness in production.
5. Deploy only when `P0-INGESTION-LAG`, `P0-FRESHNESS`, `P0-QUALITY`,
   `P0-CONTRACT-COMPATIBILITY`, `P0-SCHEMA-REGISTRY-COMPATIBILITY`, `P0-ACCESS-POLICY`,
   `P0-ACCESS-GRANT-EVIDENCE`, `P0-RETENTION-ERASURE`,
   `P0-LAKEHOUSE-SNAPSHOT-EVIDENCE` and `P0-PRODUCTION-EVIDENCE` are green.
6. Create a release promotion manifest with `enterprise-df release-promote`; promotion is blocked
   unless release evidence passed, target environment matches, output snapshot/content hash is known,
   and requester and approver are separated.
7. Create a release activation manifest with `enterprise-df release-activate`; activation updates the
   active pointer only when the promotion is approved, the activator is separated from the requester
   and production-like environments have a rollback target.
8. Publish or expose the target Gold data product only after `P0-LAKEHOUSE-SNAPSHOT-EVIDENCE`,
   `P0-GOLD-EVIDENCE`, promotion and activation are green.
9. Monitor the same gates for at least one Gold freshness interval after release.

## Alerting Policy

| Alert | Page condition | Ticket condition |
|---|---|---|
| Ingestion lag | P99 lag `> 15m` for two evaluations or any active partition stalled `> 15m`. | P95 lag `> 10m` for three evaluations. |
| Freshness | Bronze `> 15m`, Silver `> 60m`, or Gold `> 240m` for two evaluations. | Any layer reaches 75% of its SLO for three evaluations. |
| Quality | Any blocking check fails, any privacy check fails, or Gold candidate contains quarantined rows. | Non-blocking anomaly requires owner triage before the next release. |
| Contract compatibility | Compatibility status is `0` for any P0 contract. | Compatibility report missing on a release that changes schemas or contracts. |
| Gold evidence | Active Gold snapshot has evidence status `0`. | Evidence pack is incomplete during staging signoff. |

## Operating Rules

- Failed quality checks block downstream Gold publication, even when service health checks are green.
- A missing evidence pack is a failed release gate, not a documentation cleanup task.
- Do not lower SLO thresholds, downgrade check severity or bypass contract compatibility to complete a
  production release. Use the incident process and obtain explicit release owner approval for any
  temporary exception.
- Backfills must produce a new evidence pack when they replace or reactivate a Gold snapshot.
- P0 gate breaches follow the runbook in `df/ops-runbooks/data-platform-p0-gates.md`.
