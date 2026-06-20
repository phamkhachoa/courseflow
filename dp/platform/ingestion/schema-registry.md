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
  `dp/contracts/events/*.schema.json` and `dp/contracts/event-envelope.v1.schema.json` is JSON
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
referenced schemas into the registered artifact while keeping `dp/contracts` as the source of truth.

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
- Topic contract exists under `dp/contracts/topics/<topic>.yaml`.
- Payload JSON Schema exists under `dp/contracts/events/<topic>.schema.json`.
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

`enterprise-dp schema-registry-check` creates the P0 compatibility evidence artifact used by local
preflight and CI until a production registry integration is wired.

```bash
PYTHONPATH=src python -m enterprise_dp.cli schema-registry-check \
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

## Local Apicurio Runtime Smoke

`enterprise-dp schema-registry-runtime-smoke` starts the local Apicurio Registry service from
`platform/runtime/local/docker-compose.yaml`, publishes topic payload JSON Schemas through the
Confluent-compatible v7 API, applies each subject compatibility mode and reads the exact registered
schema back.

```bash
cd dp
make schema-registry-runtime-smoke
```

The report has artifact type `schema_registry_runtime_smoke_report.v1` and records:

- Apicurio system info, registry URI, group id and API mode.
- Subject, topic, product and domain for every published topic contract.
- Contract path/hash and payload schema path/hash.
- Schema id, subject version and configured compatibility mode returned by the live registry.
- Read-back hash comparison against the repository contract.
- A generated `schema_registry_publication_manifest.v1` for local review-pack attachment.

This is a local runtime publication/read-back proof. It does not claim production registry
authentication, RBAC, durable storage, HA, backup/restore, signed external attestation, producer
schema-id enforcement or broker/sink validation.

## Local Auth Enforcement Smoke

`enterprise-dp schema-registry-auth-smoke` starts a local token/RBAC gateway in front of the local
Apicurio Registry and proves the registry boundary is not open-by-default:

```bash
cd dp
make schema-registry-auth-smoke
```

The report has artifact type `schema_registry_auth_smoke_report.v1` and records:

- Publisher principal can publish a subject, set compatibility and read the schema.
- Reader principal can read but cannot publish or update compatibility.
- Missing, unknown and unprivileged tokens are rejected with `401/403`.
- Authorization decisions are audited with principal aliases, role scope and status codes.
- HTTP exchange evidence excludes bearer token values.

The production review pack consumes this report and removes
`production_registry_authentication_authorization` only when all allow/deny probes and audit checks
pass. This is local production-style auth evidence, not enterprise OIDC/Keycloak integration, secret
rotation, external API gateway/WAF, durable registry storage or registry HA.

## Local Shared Storage Smoke

`enterprise-dp schema-registry-storage-smoke` starts two Apicurio SQL registry replicas backed by
the same PostgreSQL database:

```bash
cd dp
make schema-registry-storage-smoke
```

The report has artifact type `schema_registry_storage_smoke_report.v1` and records:

- Two Apicurio SQL replicas reachable through separate local ports.
- Shared PostgreSQL storage configuration with secret values redacted and Docker env-files kept
  outside the build artifact in an OS temp directory.
- Subject publish and compatibility update through replica A.
- Latest schema, schema id/version, schema hash and compatibility read-back through replica B.
- Replica A restart followed by durable read-back.

The production review pack consumes this report and removes `production_registry_ha_storage` only
when shared SQL storage, cross-replica read-after-write and restart durable read-back all pass. This
evidence proves stateless registry replicas over shared SQL storage; it does not claim managed HA
Postgres, multi-AZ placement, load-balancer failover, backup/restore/PITR, database migration
runbooks or production secret rotation.

## Production Governance Report

`enterprise-dp schema-registry-ops-report` turns compatibility output plus registry publication
evidence into an environment-specific production gate.

Local preflight can pass with repository contracts only:

```bash
PYTHONPATH=src python -m enterprise_dp.cli schema-registry-ops-report \
  --root . \
  --environment local \
  --output build/schema-registry/schema-registry-ops.local.json
```

Staging/prod must attach a `schema_registry_publication_manifest.v1` and a signed
`external_evidence_attestation.v1` for `evidence_kind=schema_registry`:

```bash
PYTHONPATH=src python -m enterprise_dp.cli schema-registry-ops-report \
  --root . \
  --environment prod \
  --release-id <release-id> \
  --compatibility-report build/schema-registry/compatibility-report.json \
  --publication-evidence build/schema-registry/publication-prod.json \
  --attestation build/schema-registry/publication-prod.attestation.json \
  --output build/schema-registry/schema-registry-ops.prod.json
```

The production report blocks when:

- Staging/prod uses local registry evidence or lacks a production registry URI.
- Publication evidence is missing, wrong-environment or wrong artifact type.
- Signed attestation is missing, invalid, wrong-environment, wrong-release or does not hash-match
  the publication manifest.
- A subject is not registered, lacks `schema_id` or `artifact_id`, has the wrong compatibility mode,
  or the registered payload schema hash does not match the contract.
- Producer/normalizer enforcement is not proven, or broker/sink validation is not enabled.

Control Tower consumes the same artifact through `--schema-registry-ops-report`. If the artifact is
omitted, local runs generate a repository preflight report from contracts; staging/prod runs fail
closed until publication evidence and a signed external attestation are attached. Local Apicurio
publication/read-back is available through `schema-registry-runtime-smoke`; staging/prod still need
durable registry evidence collected from the actual environment.

Production review packs also accept `--schema-registry-ops-report`. The
`schema-registry-compatibility` capability blocker is removed only when the attached ops report is
`staging` or `prod`, `production_like_ready`, strict-passing, externally attested, covers the P0
source subjects and every subject carries contract hash, payload schema hash, schema/artifact id,
compatibility, producer-enforcement and broker-validation evidence. A local preflight report, a
summary-only payload and any localhost registry URI are explicitly insufficient.

## Contract Impact Report

`enterprise-dp contract-impact-report` turns compatibility evidence into a release decision. It
joins the schema registry report with catalog lineage, use-case registry and access grants so
operators can see which Bronze/Silver/Gold products, P0/P1 use cases and consumers are affected.

```bash
PYTHONPATH=src python -m enterprise_dp.cli contract-impact-report \
  --root . \
  --topic finance.billing_transaction.settled.v1 \
  --schema-registry-report build/schema-registry/compatibility-report.json \
  --output build/contract-impact/finance.billing_transaction.settled.v1.json
```

Release policy:

- `blocked`: schema compatibility failed; use a new major topic or an approved migration plan.
- `review_required`: schema compatibility passed, but downstream data products, P0/P1 use cases or
  active grants are affected; obtain topic owner, steward, domain/use-case and data product owner
  approvals before release.
- `allowed`: no breaking change and no registered downstream impact.

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
