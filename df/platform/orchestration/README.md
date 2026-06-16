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

- `enterprise-df run-use-case` is the preferred local CLI entrypoint for runnable enterprise use
  cases. It resolves the implementation from `use-cases/registry.yaml`, runs the registered pipeline,
  exports catalog lineage and writes generic release evidence.
- `local-recommendation-slice.md` documents the first end-to-end DF pilot: Bronze ingestion,
  Medallion build, catalog export and P0 release evidence.
- `enterprise-df run-recommendation-slice` remains as the backward-compatible CourseFlow LMS pilot
  command.
- `enterprise-df pipeline-list`, `enterprise-df pipeline-describe` and `enterprise-df run-pipeline`
  provide the reusable local runner interface that future products and use cases should implement
  before adding bespoke commands. `pipeline-list` can filter by product, domain, use case and output
  data product.
- `control_tower.materialize_gold.from_report.v1` materializes the P0 Data Product Control Tower
  report into four operational Gold outputs for inventory, contract compliance, quality/SLA and
  lineage coverage dashboards.
- `pipeline-registry.yaml` is the declarative control-plane manifest for runnable pipelines. Active
  entries are validated against the Python runner registry so orchestration metadata, use-case
  registry and implementation adapters cannot drift silently.
- `enterprise-df release-promote` creates a release promotion manifest from a passing release
  evidence pack. This is the audit boundary between "gates are green" and "activate this snapshot"
  and records the release evidence hash, output data product, snapshot/content hash and maker-checker
  identities.
- `enterprise-df release-activate` creates the activation manifest and updates the active pointer
  state only when the promotion is approved. Production-like activations require an existing rollback
  target, so every active data-product snapshot has an auditable previous pointer.
