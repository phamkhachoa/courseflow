# P0 Schema Registry Decision And Checklist

This standard applies to every product onboarded into the enterprise data platform. CourseFlow LMS is
the first pilot product and must not receive LMS-only exceptions that future products cannot reuse.

## Decision

The P0 platform standard is:

- Kafka topics that enter platform Bronze must be governed by a schema registry before production
  ingestion is enabled.
- The client and CI integration contract is the Confluent Schema Registry API because it is widely
  supported by Kafka clients, Kafka Connect sinks, Apicurio Registry and managed Confluent
  deployments.
- Local OSS default: Apicurio Registry running in Confluent-compatible API mode.
- Managed production option: Confluent Schema Registry when the enterprise Kafka environment is
  Confluent-managed. Apicurio remains acceptable only if it enforces the same subject naming,
  compatibility and authentication rules.
- P0 event schemas use JSON Schema because the current contract source of truth under
  `df/contracts/events/*.schema.json` and `df/contracts/event-envelope.v1.schema.json` is JSON
  Schema. Avro or Protobuf can be added later only through a new platform ADR.
- Default compatibility mode is `BACKWARD_TRANSITIVE` for every platform-ingested topic value
  subject. Breaking changes require a new major topic and a migration plan.

## Subject Naming

| Registry subject | Required for | Pattern | Example |
| --- | --- | --- | --- |
| Event value | All platform-ingested events | `<topic>-value` | `finance.benefit_settled.v1-value` |
| Event key | Topics with a structured key | `<topic>-key` | `commerce.order_submitted.v1-key` |
| CDC value | CDC sources promoted to Bronze | `<source>.<schema>.<table>.v<major>-value` | `crm_sales.public.accounts.v1-value` |
| Batch value | Governed batch feeds | `<product>.<feed>.v<major>-value` | `enterprise-commerce.settlement-export.v1-value` |

The registered value schema must validate the full platform message, including the shared envelope
and event-specific payload. If the selected registry supports schema references, the topic schema
should reference the shared envelope and payload schema. If it does not, CI should bundle the
referenced schemas into the registered artifact while keeping `df/contracts` as the source of truth.

## Topic Versioning

- Canonical event topics use `<domain>.<entity>.<event>.v<major>`.
- The topic major version must match `eventVersion` in the enterprise envelope.
- Compatible additive changes stay on the same major topic and are checked against
  `BACKWARD_TRANSITIVE`.
- A producer must dual-publish or bridge old and new topics during any breaking migration.
- Legacy or product-native outbox topics that publish raw unversioned event types, such as
  `order.submitted`, must not be written directly to approved Bronze. They need a producer change,
  dual-publish bridge or ingestion normalizer that emits the canonical versioned topic, such as
  `commerce.order_submitted.v1`, with the enterprise envelope and registry schema id.

## Compatibility Rules

Allowed without a new major version:

- Add an optional field with a default or nullable type.
- Broaden a nullable field description or documentation without changing runtime type.
- Add a non-sensitive enum value only after downstream owner review, because exhaustive consumers can
  still break even when schema compatibility passes.
- Add metadata fields that consumers can ignore.

Requires a new major topic or data product:

- Remove, rename or narrow a field.
- Add a new required field.
- Change field type, timestamp semantics, units, casing or identifier hashing logic.
- Move a field between envelope and payload.
- Change tenant, residency, PII classification, retention or access semantics.
- Reuse an existing event type for a different business fact.

## Production Release Checklist

Every platform-ingested event must pass this checklist before production Bronze is enabled:

- The source is registered in `platform/ingestion/source-registry.yaml` with an approved canonical
  topic, schema subject, bridge/normalizer mode and production evidence requirements.
- Topic contract exists under `df/contracts/topics/<topic>.yaml`.
- Payload JSON Schema exists under `df/contracts/events/<topic>.schema.json`.
- Topic contract points to `contracts/event-envelope.v1.schema.json`.
- Registry subject `<topic>-value` is created with compatibility `BACKWARD_TRANSITIVE`.
- CI validates the schema locally and checks compatibility against the registry or a registry
  compatibility report captured for the release.
- Producer publishes the canonical versioned topic, or the approved normalizer maps a legacy source
  topic to the canonical versioned topic.
- Broker or sink rejects records that do not match the registered schema.
- Bronze writer records `schema_registry_url`, `schema_subject`, `schema_id` or registry artifact
  id, and the exact source topic/partition/offset when available.
- Privacy classification and tenant isolation match the topic and Bronze data product contracts.
- Replay test proves the same source offset range can be landed twice without duplicate approved
  Bronze rows.

## Local Compatibility Report

`enterprise-df schema-registry-check` creates the P0 compatibility evidence artifact used by local
preflight and CI until a production registry integration is wired.

```bash
PYTHONPATH=src python -m enterprise_df.cli schema-registry-check \
  --root . \
  --output build/schema-registry/compatibility-report.json
```

The report has artifact type `schema_registry_compatibility_report.v1` and records:

- Registry URI or local preflight label.
- Subject name, topic, product and domain.
- Topic contract path, version and hash.
- Envelope and payload schema paths, ids, titles and hashes.
- Expected compatibility mode.
- Prior topic versions checked for local backward-transitive compatibility.
- Check results and `compatibility_passed`.

The local checker is intentionally strict enough for CI evidence but is not a substitute for broker
or registry enforcement in production. Production releases should attach a durable report URI and
hash from the selected registry workflow.

## Pilot Appendix: CourseFlow Mapping

| Canonical topic | Current CourseFlow source gap | P0 registry action |
| --- | --- | --- |
| `course.published.v1` | Backend currently emits raw `course.published` from outbox `event_type`. | Register canonical v1 subject and add producer dual-publish or normalizer bridge. |
| `enrollment.completed.v1` | Payload often needs `orgId`, `completedAt` and person hashing alignment. | Register canonical v1 subject only after normalizer fills required envelope and payload fields. |
| `gradebook.final_grade.updated.v1` | Contract/topic naming must align on underscore form and required grade fields. | Register only the underscore canonical subject; reject hyphenated alias from approved Bronze. |
| `recommendation.tracking.v1` | Current source is HTTP/table based, not a Kafka producer. | Choose collector event topic, analytics outbox or CDC bridge, then register the canonical value subject. |

## Open Follow-Ups

- Decide the enterprise production registry vendor after Kafka environment ownership is finalized.
- Add registry authentication and RBAC mapping under platform security.
- Add automated publication to Apicurio or Confluent after the registry vendor is finalized.
