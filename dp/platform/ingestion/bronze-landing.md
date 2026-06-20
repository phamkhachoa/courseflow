# P0 Bronze Landing Specification

Bronze is the immutable replay layer for enterprise source records. It is shared platform
infrastructure, not a single-product warehouse. Pilot products prove the pattern for later products
without defining the platform vocabulary.

## Landing Principles

- Land only platform-approved records into approved Bronze tables.
- Preserve enough raw source material, offsets, hashes and schema metadata to replay or audit the
  record.
- Keep Bronze append-only from the ingestion path. Corrections are modeled as new source records or
  quarantine actions, not in-place mutation of approved Bronze rows.
- Do minimal parsing: extract envelope, source lineage, event time, tenant keys, hashes and the
  contract-required columns.
- Do not let direct identifiers leak into approved Bronze when the contract requires hashed or
  tokenized identifiers.
- Treat operational CSV exports as temporary backfill/reference sources, not canonical Bronze feeds,
  unless they have a source contract, stable source position and replay controls.

## Approved Bronze Table Types

| Type | Use for | Naming pattern | Example |
| --- | --- | --- | --- |
| Event table | Versioned business facts from outbox, collector or normalized event sources | `bronze.events_<domain>_<fact>` | `bronze.events_order_submitted` |
| CDC change table | Row-level state replication from Debezium or equivalent CDC | `bronze.cdc_<product>_<source_schema>_<table>` | `bronze.cdc_crm_sales_public_accounts` |
| Batch receipt table | Governed files or SaaS extracts with manifest control | `bronze.batch_<product>_<feed>` | `bronze.batch_hris_employee_export` |
| Quarantine table | Rejected records that need secure triage | `bronze_quarantine.<source_name>` | `bronze_quarantine.order_submitted` |

Approved Bronze data product contracts live under `dp/contracts/data-products`. The physical Iceberg
table naming and partition rules are defined in `dp/platform/lakehouse/iceberg-table-standards.md`.

## Required Columns For Event Bronze

P0 event Bronze tables must expose these columns or an explicitly documented superset:

| Column | Type | Required | Notes |
| --- | --- | ---: | --- |
| `product_id` | string | yes | Enterprise product code such as `enterprise-commerce`. |
| `domain_id` | string | recommended | Enterprise data domain when available. |
| `event_id` | string/uuid | yes | Global idempotency key from the envelope or approved normalizer. |
| `event_type` | string | yes | Canonical versioned event type, for example `commerce.order_submitted.v1`. |
| `event_version` | int | yes | Major version from the envelope. |
| `source_service` | string | yes | Producing service or normalizer service. |
| `tenant_id` | string | conditional | Required when the product uses tenant ids instead of org ids. |
| `org_id` | string/uuid | conditional | Required when the product uses organization boundaries. |
| `occurred_at` | timestamp | yes | Business event time. |
| `published_at` | timestamp | yes | Source publish time or bridge publish time. |
| `ingested_at` | timestamp | yes | Platform Bronze landing time in UTC. |
| `source_system` | string | yes | Logical source system name from the source registry. |
| `source_topic` | string | conditional | Kafka topic or equivalent stream name. |
| `source_partition` | int | conditional | Kafka partition when available. |
| `source_offset` | long | conditional | Kafka offset when available. |
| `source_snapshot_id` | string | conditional | CDC snapshot, file manifest or source export id when no Kafka offset exists. |
| `source_record_key` | string | recommended | Non-sensitive source key or tokenized key. |
| `source_record_hash_sha256` | string | yes | Hash of canonical source identity and raw bytes. |
| `payload_hash_sha256` | string | yes | Hash of the platform-approved payload bytes. |
| `schema_subject` | string | yes | Registry subject used for validation. |
| `schema_id` | string | yes | Registry schema id, version or artifact id. |
| `raw_headers` | json/map | recommended | Source headers after secret stripping. |
| `raw_payload` | json/string | yes | Platform-approved raw payload for replay. |
| `ingest_run_id` | string | yes | Orchestrator or sink run id. |
| `event_date` | date | yes | Derived from `occurred_at` for partition pruning. |
| `ingest_date` | date | yes | Derived from `ingested_at` for operational triage. |

Existing P0 contract drafts already include the core envelope and source position columns. Before
production signoff, reconcile each contract against this required column list or document a narrow
exception with the platform owner.

## Raw Payload And PII Handling

Approved Bronze can preserve only the payload that is allowed by the topic and data product contract.
If the source emits direct identifiers but the contract requires hashed values:

1. The producer, bridge or normalizer must tokenize or hash identifiers before approved Bronze.
2. The exact direct-identifier source bytes may be stored only in a restricted secure quarantine or
   raw-secure path with explicit retention, access and erasure controls.
3. `raw_payload` in the approved Bronze data product must contain the platform-approved payload, not
   forbidden direct identifiers.
4. The hash salt/pepper must come from secrets management, not source code or local config files.

For any pilot product, direct person, account, profile or session identifiers must be converted to
contract-approved tokenized fields before the approved Bronze event tables are published.

## Landing Flow

1. Read from the source topic, CDC feed, collector receipt table or batch manifest.
2. Validate the record against the schema registry or source contract.
3. Normalize legacy source names to canonical platform names when an approved bridge is used.
4. Extract source position, event time, tenant keys and contract-required fields.
5. Compute `source_record_hash_sha256` and `payload_hash_sha256`.
6. Write to a staging table or temp file set tied to `ingest_run_id`.
7. Commit into the target Iceberg table using an idempotent append or merge pattern.
8. Persist offset ranges, source snapshot ids, row counts, rejected counts and quality summary.
9. Send invalid records to quarantine with a reason code and source lineage.

## Quarantine Reasons

Use stable reason codes so operations can alert and trend them:

- `SCHEMA_INVALID`
- `COMPATIBILITY_UNKNOWN`
- `MISSING_TENANT`
- `PII_POLICY_VIOLATION`
- `EVENT_TIME_INVALID`
- `SOURCE_POSITION_MISSING`
- `DUPLICATE_SOURCE_POSITION`
- `HASH_MISMATCH`
- `NORMALIZATION_FAILED`

Quarantined rows are not eligible for Silver or Gold until corrected through an approved replay or
source fix.

## P0 Acceptance Criteria

A Bronze table is production-ready only when:

- It has a data product contract with owner, steward, privacy, retention and quality metadata.
- Its source is listed in `dp/platform/ingestion/source-systems.md` or the next product-specific
  source registry.
- It lands the required lineage, hash and schema metadata.
- It can be replayed over a bounded source offset or snapshot range without duplicate approved rows.
- It has freshness and quality checks wired into the P0 release gates.
- It is queryable through the approved Iceberg catalog, not by direct object path reads.
