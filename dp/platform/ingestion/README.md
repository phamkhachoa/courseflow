# Ingestion Platform

Ingestion covers Kafka topics, transactional outbox events, Debezium CDC sources and batch ELT
connectors.

## P0 Work

- Define topic naming conventions: `<domain>.<entity>.<event>.v<major>`.
- Register each product source in [source-registry.yaml](source-registry.yaml) before enabling
  Bronze ingestion.
- Map product outbox events to the shared enterprise envelope. Product-specific source notes belong
  under `products/<product-code>/` or explicit pilot appendices.
- For sources that cannot publish the canonical envelope directly, run `enterprise-dp
  source-bridge-normalize` as the source bridge preflight and attach the resulting bridge manifest to
  the readiness gate.
- Apply the P0 schema registry decision and release checklist in
  [schema-registry.md](schema-registry.md).
- Land platform-approved source records according to
  [bronze-landing.md](bronze-landing.md).
- Use [local-bronze-ingestion.md](local-bronze-ingestion.md) as the local preflight before wiring a
  topic into the production sink.
- Promote a source only through
  [source-to-bronze-readiness.md](source-to-bronze-readiness.md), which combines registry,
  bridge, ingestion, replay, offset ledger, schema, change-control, catalog and lineage evidence.
- Track source offsets, hashes and idempotency keys according to
  [source-offset-hash-idempotency.md](source-offset-hash-idempotency.md).
- Gate live event/outbox/CDC connector readiness through
  [event-cdc-ingestion-runtime.md](event-cdc-ingestion-runtime.md) and
  `enterprise-dp ingestion-runtime-check` before production signoff.
- Create first Bronze sink specs for:
  - `finance.benefit_settled.v1`
  - `commerce.order_submitted.v1`
  - `customer.profile_updated.v1`
  - `hris.employee_status_changed.v1`
  - `recommendation.tracking.v1`

## Rules

- Ingestion must preserve original event payload, headers, source offsets and ingestion timestamp.
- A bridge or normalizer must preserve source topic, partition and offset while producing the
  canonical versioned topic and approved payload shape.
- Consumers must be idempotent by `eventId` plus source topic/partition/offset.
- CDC should be used for state replication; outbox events should be preferred for business facts.
- Production-like source activation must have a passing `source_readiness_report.v1`.
- Production-like Bronze commits must have a passing `source_offset_ledger.v1` with Iceberg snapshot
  evidence.
- Production-like event and CDC ingestion must have a passing
  `event_cdc_ingestion_runtime_report.v1` with non-synthetic runtime evidence, healthy connectors,
  lag within SLO, DLT coverage, clear backpressure and attached offset ledger hashes.

## Implemented Local Evidence

- `enterprise-dp transactional-outbox-smoke` proves a local source Postgres outbox can be polled,
  published through Redpanda and consumed back into the Bronze ingestion preflight.
- `enterprise-dp live-bronze-ingestion-smoke` extends that slice into the data plane: source
  Postgres outbox rows are published to Redpanda with topic/partition/offset evidence, approved
  records are appended to a Bronze Iceberg table on MinIO through PyIceberg, Trino reads the table
  back, duplicate events are skipped idempotently, invalid schema records are quarantined and restart
  resume is proven from the offset ledger.
- These local proofs are suitable for partner architecture/evidence review. They do not replace
  production Debezium/Kafka Connect or outbox-relay deployment evidence, connector HA, connector
  secret rotation, backpressure policy, multi-source rollout or broker audit export.
