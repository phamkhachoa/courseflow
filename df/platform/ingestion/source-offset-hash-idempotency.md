# Source Offset, Hash And Idempotency Standard

This standard defines how ingestion proves that source records are complete, replayable and
deduplicated. It applies to all enterprise products. CourseFlow LMS is the first pilot source set.

## Idempotency Decision

Bronze ingestion is at-least-once at the transport layer and idempotent at the table layer. Streaming
checkpoints are operational hints, not the source of truth for correctness.

The preferred idempotency key order is:

1. `source_topic`, `source_partition`, `source_offset` for Kafka records.
2. CDC source position, such as connector name plus database, schema, table and log sequence
   position.
3. Batch manifest identity, file checksum and row ordinal for governed files.
4. Collector receipt id plus event id for HTTP or mobile collector events.
5. `event_id` plus `product_id`, `source_service` and `event_type` only when no stronger source
   position exists.
6. `source_record_hash_sha256` only as a last-resort duplicate detector, not as the primary replay
   cursor.

Approved Bronze must reject or quarantine a duplicate primary source position for the same target
table unless the duplicate row is byte-for-byte equivalent to the already committed row.

## Required Source Position Fields By Source Type

| Source type | Required source position | Replay boundary |
| --- | --- | --- |
| Kafka outbox topic | Topic, partition, offset, key, timestamp, schema id | Offset range per topic partition |
| Debezium CDC | Connector name, source database, schema, table, LSN/binlog/file-position, snapshot flag | CDC log position or snapshot id |
| HTTP collector | Collector receipt id, received timestamp, optional client event id, request batch ordinal | Receipt id range or collector table snapshot |
| Governed file/batch | Manifest id, object URI, object version or ETag, file hash, row ordinal | Manifest id plus object versions |
| SaaS connector | Connector run id, source object id, source updated timestamp, page/cursor token when exposed | Connector run id and cursor range |

If a source cannot provide one of these positions, it is not production-ready for approved Bronze.

## Hashes

Use lowercase hex SHA-256 for all P0 ingestion hashes.

| Hash column | Input | Purpose |
| --- | --- | --- |
| `source_record_hash_sha256` | Source identity, source position, source key, raw headers after secret stripping and raw source bytes | Detect duplicate or changed source records during replay. |
| `payload_hash_sha256` | Canonicalized platform-approved payload bytes | Prove payload stability after normalization/tokenization. |
| `source_key_hash_sha256` | Source key bytes when the key is sensitive or too large to store directly | Join-safe lineage without exposing direct identifiers. |
| `file_hash_sha256` | Exact file bytes for batch inputs | Detect upstream file replacement or partial transfer. |

Canonical JSON hashing must use deterministic key ordering, UTF-8 encoding, no insignificant
whitespace and normalized timestamp strings. Do not hash pretty-printed JSON produced by ad hoc
debug tooling.

## Offset Ledger

Each production ingestion job must emit an offset ledger entry for every commit attempt:

| Field | Description |
| --- | --- |
| `ingest_run_id` | Stable id for the ingestion run or streaming micro-batch. |
| `target_table` | Iceberg table receiving the records. |
| `source_name` | Logical source from the source registry. |
| `source_type` | Kafka, CDC, collector, batch or SaaS. |
| `start_position` | Inclusive low watermark by partition, cursor or manifest. |
| `end_position` | Exclusive high watermark by partition, cursor or manifest. |
| `input_record_count` | Records read from source. |
| `committed_record_count` | Records committed to approved Bronze. |
| `quarantined_record_count` | Records rejected with reason codes. |
| `duplicate_record_count` | Records skipped because their source position already exists. |
| `target_snapshot_id` | Iceberg snapshot id after commit. |
| `status` | Started, committed, failed or rolled back. |

The ledger may live in an operational metadata schema, but it must be queryable during incident
response and included in Gold evidence packs.

`enterprise-df offset-ledger-record` creates `source_offset_ledger.v1` from a Bronze ingestion
manifest and replay manifest. The ledger records partition watermarks, committed/quarantined/duplicate
counts, row-hash bindings and Iceberg snapshot metadata. `source_readiness_report.v1` requires this
ledger in production-like environments.

## Replay Rules

- Replay must be requested by source position range, source snapshot id or batch manifest id.
- Replays must write the same target table and preserve original `occurred_at`, `published_at`,
  schema metadata and hashes.
- Replays may have a new `ingest_run_id` and `ingested_at`.
- Replays must produce zero additional approved Bronze rows when the same source records already
  exist and are equivalent.
- If the same source position produces a different hash, stop the replay and quarantine with
  `HASH_MISMATCH`.
- Never advance the committed high watermark until the Iceberg table commit succeeds.

## CourseFlow P0 Defaults

| Source | Primary idempotency key | Notes |
| --- | --- | --- |
| `course.published.v1` | Kafka topic, partition and offset after the versioned bridge | The bridge must preserve original raw topic and offset in source metadata. |
| `enrollment.completed.v1` | Kafka topic, partition and offset after the versioned bridge | Use `event_id` as a secondary duplicate detector. |
| `gradebook.final_grade.updated.v1` | Kafka topic, partition and offset after the versioned bridge | Reject hyphenated topic aliases from approved Bronze. |
| `recommendation.tracking.v1` | Depends on selected source path | If HTTP/table source remains P0, use collector receipt id or CDC position, not only event id. |

## Checklist

- Source position fields are present and non-null for the selected source type.
- Idempotency key is declared in the Bronze data product contract or ingestion spec.
- Hashes are computed in a deterministic library shared by batch and streaming jobs.
- Duplicate source positions are counted and visible in observability.
- Replay from the previous committed offset range is tested before production signoff.
- Offset ledger entries are attached to release evidence for every P0 Bronze table.
