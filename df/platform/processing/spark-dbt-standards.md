# P0 Spark And dbt Processing Standards

Processing standards are platform-wide. The first pilot workload covers Bronze-to-Silver activity
and Gold recommendation interaction datasets, but the runtime patterns must work for future
enterprise products.

## Engine Placement

| Engine | Use for | Avoid using for |
| --- | --- | --- |
| Spark batch | Heavy Bronze-to-Silver transforms, historical backfills, CDC compaction, large joins, feature snapshot builds | Small SQL-only marts that dbt can express clearly |
| Spark Structured Streaming | Low-latency Bronze landing or streaming enrichment with bounded state and clear SLO | Business logic that can tolerate scheduled batch processing |
| dbt Core | SQL-first Silver/Gold models, tests, docs, metric marts, exposures | Raw source ingestion, Kafka/CDC offset management, complex stateful streaming |
| Flink/Kafka Streams | Sub-minute event processing with explicit real-time SLO | P0 default transformations without a real-time requirement |

## Shared Rules

- Read only from approved Iceberg Bronze or Silver tables unless a backfill source exception is
  approved by the platform owner.
- Never read product OLTP databases directly from transformation jobs.
- Use catalog table identifiers such as `prod_lakehouse.bronze.events_order_submitted`, not
  direct object paths.
- All jobs must accept environment, input table/snapshot or source offset range, output table and
  run id as parameters.
- All jobs must be deterministic for the same input snapshots and parameters.
- Use UTC timestamps internally. Convert to local business calendars only in clearly named output
  columns.
- Emit row counts, duplicate counts, rejected counts, freshness lag and output snapshot id.
- Do not publish Gold outputs unless quality gates pass.
- After every production-like Silver/Gold Iceberg commit, emit `lakehouse_snapshot_evidence.v1` with
  the pipeline manifest hash, Iceberg snapshot metadata, schema and partition evidence, contract
  hashes and upstream offset-ledger binding. The release gate rejects staging/prod publication when
  this evidence is missing or points at a different snapshot.

## Spark Job Standard

Spark jobs must:

- Use the configured Iceberg catalog for all reads and writes.
- Lock dependency versions and avoid runtime package downloads in production.
- Use named columns and explicit schemas for JSON parsing.
- Keep source lineage columns through Silver unless a contract explicitly drops them.
- Deduplicate using the idempotency standard from
  `df/platform/ingestion/source-offset-hash-idempotency.md`.
- Use event-time watermarks only when the late-arrival policy is documented.
- Write through staging tables or partition-scoped commits when replaying or backfilling.
- Fail fast on schema mismatch rather than silently adding, dropping or coercing fields.
- Emit an evidence artifact for every successful production run.

Spark jobs must not:

- Use `current_timestamp()` for business event time.
- Generate random ids in output records unless the generated id is deterministic from source keys.
- Overwrite an entire table when the intended operation is a partition or snapshot replacement.
- Drop quarantine rows into Silver or Gold.
- Depend on local files that are not versioned or registered as input artifacts.

## dbt Model Standard

dbt projects must:

- Declare Bronze and Silver inputs as `sources` with freshness expectations where supported.
- Use model names that match data product names where practical, for example
  `silver_customer_activity` for `silver.customer_activity`.
- Materialize Silver and Gold incrementally unless the table is small enough for a full rebuild and
  the rebuild is documented.
- Use explicit column contracts and docs for published models.
- Include tests for not-null keys, uniqueness, accepted values, relationships, event-time bounds,
  tenant/org presence and PII policy assumptions.
- Declare exposures for BI, ML, reverse ETL or API consumers of Gold models.
- Attach quality results and documentation links to the Gold evidence pack.

dbt models must not:

- Read unapproved source schemas or product OLTP databases.
- Parse raw payload JSON repeatedly in multiple downstream models when a staged model should own the
  extraction.
- Hide breaking semantic changes in a view without a data product contract update.
- Use environment-specific object paths in SQL.

## Backfill Standard

Every backfill must define:

- Target data product and table.
- Input Bronze/Silver snapshot ids or source offset ranges.
- Event-time range and partition list.
- Tenant scope and affected downstream consumers.
- Code version or container image.
- Quality suite and expected row-count checks.
- Replay/idempotency behavior.
- Rollback or withdrawal plan for downstream Gold consumers.
- `backfill_readiness_report.v1` from `enterprise-df backfill-readiness-check` before
  production-like execution.

Backfills should run in this order:

1. Land or replay missing Bronze source positions.
2. Rebuild affected Silver partitions from exact Bronze snapshots.
3. Rebuild affected Gold partitions or snapshots from exact Silver snapshots.
4. Publish evidence and notify consumers only after quality gates pass.

## Quality Gates

Minimum P0 checks:

| Layer | Blocking checks |
| --- | --- |
| Bronze | Source position unique, event id not null, tenant/org present, event type allowed, schema id present, no forbidden direct identifiers. |
| Silver | Business keys not null, source event id unique at target grain, event time within accepted bounds, tenant isolation, PII classification complete. |
| Gold | Grain uniqueness, metric sanity bounds, freshness SLO, source lineage present, access policy and evidence pack complete. |

## Non-Normative Pilot Processing Slice

| Dataset | Engine default | Notes |
| --- | --- | --- |
| `bronze.events_*` | Spark Structured Streaming or Kafka Connect Iceberg sink plus validation job | Must preserve source offsets and schema ids. |
| `silver.learner_activity` | Spark batch first, dbt acceptable after event extraction is simple and stable | Pilot table for activity events. |
| `gold.recsys_interactions` | dbt incremental or Spark batch depending on volume | Must publish snapshot id for ML training. |

## Promotion Checklist

- Job reads approved catalog tables only.
- Job parameters include input snapshot or offset range.
- Output write is idempotent for a rerun with the same parameters.
- Required quality checks pass locally and in staging.
- Evidence includes code version, input snapshots, output snapshot, row counts and quality report.
- Evidence includes `enterprise-df snapshot-evidence-record` output for every Silver/Gold release
  candidate before promotion or activation.
- Owner, steward and consumer contract metadata are registered before Gold publication.
