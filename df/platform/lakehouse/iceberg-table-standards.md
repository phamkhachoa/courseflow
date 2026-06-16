# P0 Iceberg Table Naming And Partitioning Standard

Apache Iceberg is the P0 table format for Bronze, Silver and Gold. This standard is group-wide:
CourseFlow LMS is the first pilot product, not the naming authority for the enterprise platform.

## Table Identifier

Use three-part identifiers through the approved catalog:

```text
<catalog>.<layer_namespace>.<table_name>
```

Examples:

```text
local_lakehouse.bronze.events_order_submitted
prod_lakehouse.silver.customer_activity
prod_lakehouse.gold.finance_revenue_daily
```

Rules:

- Use lowercase snake_case for namespaces, tables and columns.
- Do not read or write Iceberg tables through direct object paths in processing jobs.
- The catalog name is environment-specific. Table namespaces and names are portable across
  environments.
- Layer namespaces are `bronze`, `silver`, `gold` and restricted operational namespaces such as
  `bronze_quarantine` or `platform_metadata`.
- Table names omit compatible schema minor versions. A breaking major version uses a new table only
  when both versions must be served in parallel, for example `events_order_submitted_v2`.

## Naming Patterns

| Layer | Pattern | Example |
| --- | --- | --- |
| Bronze event | `events_<domain>_<fact>` | `events_order_submitted` |
| Bronze CDC | `cdc_<product>_<source_schema>_<table>` | `cdc_crm_sales_public_accounts` |
| Bronze batch | `batch_<product>_<feed>` | `batch_hris_employee_export` |
| Silver conformed | `<business_entity_or_activity>` | `customer_activity` |
| Silver bridge | `<left_entity>_<right_entity>_bridge` | `account_product_bridge` |
| Gold mart | `<business_metric_or_product>_<grain>` | `finance_revenue_daily` |
| ML feature/snapshot | `<use_case>_<feature_or_snapshot>` | `next_best_action_features` |

The contract filename may include `.v1.yaml`; the physical table should stay stable across compatible
contract updates.

## Partitioning

Prefer Iceberg hidden partition transforms over manually encoded path partitions.

| Table type | Default partition spec | Notes |
| --- | --- | --- |
| Bronze events | `days(occurred_at)`, `source_service`, `bucket(32, org_id)` when `org_id` exists | Logical contract strategy remains event date, source service and org boundary. Use identity `org_id` only when tenant count is small and approved. |
| Bronze CDC | `days(_cdc_commit_at)`, `source_table`, `bucket(32, primary_key_hash)` | Keep source log order columns for replay. |
| Bronze batch | `ingest_date`, `source_feed`, `manifest_id` | Manifest id must be low enough cardinality for pruning. |
| Silver activity/facts | `days(event_time)`, `product_id`, optional `bucket(32, org_id)` | Partition by business event time, not ingestion time. |
| Silver dimensions | Usually unpartitioned or `bucket(32, business_key_hash)` | Avoid tiny partitions for small dimensions. |
| Gold daily marts | `business_date`, optional `product_id` or region | Publish complete partitions atomically. |
| Gold snapshots/features | `snapshot_date` or `snapshot_id` | Snapshot id must be recorded in evidence packs. |

Partition evolution is allowed, but every change must be tied to a migration note and query
validation. Do not use high-cardinality identity partitions for person, account, session, event id
or source offset.

## Required Table Properties

P0 Iceberg tables should use:

```text
format-version=2
write.parquet.compression-codec=zstd
write.target-file-size-bytes=536870912
commit.retry.num-retries=4
history.expire.max-snapshot-age-ms=7776000000
history.expire.min-snapshots-to-keep=20
```

Use a lower target file size such as 128 MB only for local development or very small pilot tables.
Production compaction should move toward 512 MB target files for scan efficiency.

## Schema Evolution

Allowed:

- Add nullable columns.
- Add documentation, PII tags or policy metadata.
- Widen a decimal precision when consumers are compatible.
- Add a new optional struct field.

Requires migration:

- Rename, drop or reorder fields in a way that breaks readers.
- Change event-time meaning, timezone or unit.
- Change identifier hashing inputs.
- Change nullability from nullable to required.
- Change privacy classification, retention or row-level isolation.

Never rely on positional column matching. Writers must use named columns.

## Write Patterns

| Layer | Write pattern | Requirement |
| --- | --- | --- |
| Bronze | Append with source-position duplicate protection, or merge from staging for replay | Preserve original source lineage and hashes. |
| Silver | Incremental merge or partition overwrite from approved Bronze/Silver inputs | Deduplicate by source event id or source position. |
| Gold | Atomic replace of a complete partition or snapshot | Block publication when quality gates fail. |
| Quarantine | Append-only | Include reason code and source lineage. |

Gold tables must publish an evidence pack with input snapshots, quality report, row counts, output
snapshot id and access policy confirmation.

## Retention And Maintenance

- Bronze data retention follows the data product contract and product onboarding defaults unless a
  stricter regulatory policy applies.
- Iceberg snapshot retention is operational and shorter than data retention. Keep enough snapshots to
  support audit, rollback and reproducible backfill windows.
- Run small-file compaction for streaming Bronze tables at least daily in production.
- Run orphan file cleanup only after the maximum job retry and object-store consistency window.
- Do not expire snapshots needed by an open incident, audit, model training evidence pack or
  regulatory hold.

## Pilot Appendix: CourseFlow Tables

The following tables are pilot evidence only. They are not the naming authority for the enterprise
platform.

| Contract | Iceberg table | Partition notes |
| --- | --- | --- |
| `bronze.events_course_published.v1.yaml` | `bronze.events_course_published` | `days(occurred_at)`, `source_service`, org bucket or identity depending on tenant count. |
| `bronze.events_enrollment_completed.v1.yaml` | `bronze.events_enrollment_completed` | Same Bronze event default; person id hashes must not be identity partitions. |
| `bronze.events_gradebook_final_grade_updated.v1.yaml` | `bronze.events_gradebook_final_grade_updated` | Same Bronze event default; grading ids can be sorted, not partitioned. |
| `bronze.events_recommendation_tracking.v1.yaml` | `bronze.events_recommendation_tracking` | Same Bronze event default; session hash must not be an identity partition. |
| `silver.learner_activity.v1.yaml` | `silver.learner_activity` | Partition by activity event time and product/org boundary. |
| `gold.recsys_interactions.v1.yaml` | `gold.recsys_interactions` | Partition by snapshot date or business date used by ML training. |
