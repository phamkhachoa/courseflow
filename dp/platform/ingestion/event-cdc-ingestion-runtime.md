# Event And CDC Ingestion Runtime Gate

`event_cdc_ingestion_runtime_report.v1` is the P0 runtime gate for live event, outbox, CDC and
batch connector movement into Bronze. It is product-agnostic and applies to every active source in
`platform/ingestion/source-registry.yaml`.

## Decision

`enterprise-dp ingestion-runtime-evidence-normalize` turns machine exports into
`ingestion_runtime_evidence.v1`. `enterprise-dp ingestion-runtime-check` consumes that evidence and
produces the P0 readiness report. Local environments may pass as a developer preflight without
machine evidence. Staging and production must attach `ingestion_runtime_evidence.v1` generated from
runtime systems such as Kafka Connect, Debezium monitoring, broker topic/ACL checks, DLT metrics,
consumer lag monitoring and offset ledger artifacts.

Control Tower consumes the report through `--ingestion-runtime-report` and blocks production signoff
when the artifact is missing, from the wrong environment, not `production_like_ready`, or when any P0
source has runtime failures.

## Evidence Contract

The attached `ingestion_runtime_evidence.v1` must include:

| Field | Purpose |
|---|---|
| `environment` | Must match the target Control Tower environment. |
| `source_kind` | Must be `ci_tool_output` or `external_attestation` for staging/prod. |
| `generated_at`, `valid_until` | Prevents stale runtime evidence from being reused. |
| `connectors[]` | One row per registered source that has runtime movement enabled. |
| `deployment_state`, `tasks_running`, `tasks_total` | Proves the connector is running and all tasks are healthy. |
| `lag.max_lag_records`, `lag.max_lag_seconds` | Proves the connector is within freshness SLO. |
| `dlt.enabled`, `dlt.topic`, `dlt.unresolved_count` | Proves failures are routed and triaged. |
| `backpressure_state` | Proves the runtime is not throttled or blocked. |
| `offset_ledger.uri`, `offset_ledger.hash` | Binds runtime commits to replayable source offsets. |

## CLI Flow

```bash
enterprise-dp ingestion-runtime-evidence-normalize \
  --root . \
  --environment prod \
  --source-kind ci_tool_output \
  --kafka-connect-status build/raw/kafka-connect-status.json \
  --lag-metrics build/raw/lag-metrics.json \
  --dlt-report build/raw/dlt-report.json \
  --backpressure-report build/raw/backpressure-report.json \
  --offset-ledgers build/raw/offset-ledgers.json \
  --broker-checks build/raw/broker-checks.json \
  --valid-until 2026-06-16T14:00:00Z \
  --output build/evidence/ingestion-runtime-prod.json

enterprise-dp ingestion-runtime-check \
  --root . \
  --environment prod \
  --evidence build/evidence/ingestion-runtime-prod.json \
  --output build/evidence/event-cdc-ingestion-runtime-prod.json
```

The normalizer writes a companion `ingestion_runtime_evidence_manifest.v1` with evidence hash, input
hashes and `readiness_args` for CI/CD. The check command exits non-zero when global evidence checks
fail or any P0 source fails the runtime checks. The report exposes `decision_board.page_now` so
support and SRE queues can page the right owner for connector outage, lag, DLT backlog, backpressure,
topic/ACL failure or missing offset ledger evidence.

## P0 Blocking Rules

- Staging/prod evidence is not attached, synthetic, expired or from the wrong environment.
- A registered P0 source has no runtime connector evidence.
- Connector deployment is not running or task count is incomplete.
- Consumer lag exceeds the configured record or age SLO.
- DLT routing is disabled, missing a topic or has unresolved records above SLO.
- Backpressure is active.
- Broker topic or producer/consumer ACL evidence is not ready.
- Offset ledger URI/hash is missing, so replay and reconciliation cannot be proven.

## Current State

This repository now has the evidence normalizer, report contract, CLI, Control Tower gate and
automated tests. It is not yet L3 production-ready until live staging/prod exporters feed the
normalizer with non-synthetic Kafka Connect, Debezium, Prometheus and broker/security evidence.
