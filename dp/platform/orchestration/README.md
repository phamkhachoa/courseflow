# Orchestration Platform

The preferred orchestrator for new enterprise data assets is Dagster because its asset-centric model
fits data products, lineage and quality gates well. Airflow remains acceptable if the deployment team
standardizes on it.

## Required Controls

- Retry with bounded attempts.
- Backfill by event date range.
- Idempotent materialization.
- Quality checks before publishing downstream assets.
- Freshness and failure metrics exported to Prometheus.

## Implemented Local Slice

- `enterprise-dp run-use-case` is the preferred local CLI entrypoint for runnable enterprise use
  cases. It resolves the implementation from `use-cases/registry.yaml`, runs the registered pipeline,
  exports catalog lineage and writes generic release evidence.
- `local-recommendation-slice.md` documents the first end-to-end DP pilot: Bronze ingestion,
  Medallion build, catalog export and P0 release evidence.
- `enterprise-dp run-recommendation-slice` remains as the backward-compatible CourseFlow LMS pilot
  command.
- `enterprise-dp pipeline-list`, `enterprise-dp pipeline-describe` and `enterprise-dp run-pipeline`
  provide the reusable local runner interface that future products and use cases should implement
  before adding bespoke commands. `pipeline-list` can filter by product, domain, use case and output
  data product.
- `control_tower.materialize_gold.from_report.v1` materializes the P0 Data Product Control Tower
  report into four operational Gold outputs for inventory, contract compliance, quality/SLA and
  lineage coverage dashboards.
- `pipeline-registry.yaml` is the declarative control-plane manifest for runnable pipelines. Active
  entries are validated against the Python runner registry so orchestration metadata, use-case
  registry and implementation adapters cannot drift silently.
- `enterprise-dp release-promote` creates a release promotion manifest from a passing release
  evidence pack. This is the audit boundary between "gates are green" and "activate this snapshot"
  and records the release evidence hash, output data product, snapshot/content hash and maker-checker
  identities.
- `enterprise-dp release-activate` creates the activation manifest and updates the active pointer
  state only when the promotion is approved. Production-like activations require an existing rollback
  target, so every active data-product snapshot has an auditable previous pointer.
- `enterprise-dp dagster-orchestration-smoke` runs a real local Dagster in-process job over the
  finance live lakehouse, object-store and Trino smoke evidence. It records the Dagster run ID, reads
  back the Dagster event log and writes `dagster_orchestration_smoke_report.v1` for the production
  review pack. This closes the local run-history proof while leaving daemon scheduling, distributed
  execution, production retry policy, backfill materialization history and service identity as P0
  production runtime gaps.
- `enterprise-dp dagster-day2-smoke` runs a focused local Dagster Day-2 smoke for retry events,
  schedule tick ledger and backfill partition materialization history. The production review pack
  can attach `dagster_day2_smoke_report.v1` so reviewers can inspect retry, tick and materialization
  evidence. A strict passing report closes the review-pack gaps for schedule tick history, retry
  backoff policy and backfill materialization history. This is deliberately scoped as local
  in-process evidence: it does not remove production P0 blockers for Dagster daemon HA, distributed
  or Kubernetes run launchers, managed run storage, production backfill scheduling or orchestrator
  metrics export.
- `enterprise-dp orchestration-runtime-ops-report` is the production-like runtime evidence gate. It
  does not run a local Dagster cluster; it evaluates `managed_orchestration_runtime_evidence.v1`
  from staging/prod and writes `orchestration_runtime_ops_report.v1`. The evidence must prove a
  redacted, fresh and externally attested runtime with release/change binding, git SHA, image digest,
  Dagster service identity, daemon/scheduler/worker HA, distributed executor or Kubernetes run
  launcher, managed run storage, schedule tick history, retry/backoff history, backfill
  materialization history, service identity authorization, secret injection, metrics/alerts and
  audit export. The production review pack removes production orchestration runtime gaps only when
  this report is strict-passing; it still leaves platform IaC and other capability gates to their
  own evidence reports.
