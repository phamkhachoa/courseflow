# Processing Platform

Processing owns reusable transformation runtime standards for Bronze-to-Silver, Silver-to-Gold,
streaming enrichment and backfill workloads.

## Scope

- Spark batch jobs for heavy transformations and historical backfills.
- dbt models for SQL-first Silver/Gold transformations, tests and documentation.
- Flink or Kafka Streams only when a use case has a clear real-time SLO.
- Common packaging, dependency, retry and idempotency rules for transformation jobs.
- Reusable materialization patterns for snapshots, partitions and evidence packs.

## Rules

- Processing jobs must read from approved Bronze/Silver inputs, not product OLTP databases.
- Spark and dbt work must follow
  [spark-dbt-standards.md](spark-dbt-standards.md).
- Production-like backfill and replay operations must follow
  [backfill-replay-governance.md](backfill-replay-governance.md).
- Local medallion preflight should follow
  [local-medallion-build.md](local-medallion-build.md).
- Every Gold-producing job must emit quality results and publish evidence.
- Backfills must be deterministic, resumable and tied to source offsets or table snapshots.
