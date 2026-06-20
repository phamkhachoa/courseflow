# Enterprise Data Platform

`dp/` is the implementation home for the group-wide enterprise data platform. It is intentionally a
top-level workspace, beside `ai/` and `backend/`, because it owns analytical data products,
lakehouse pipelines, data contracts, catalog metadata, quality gates, governance policy and ML/AI
feature handoff across many enterprise products.

CourseFlow LMS is the first onboarded product. Enterprise Commerce is the first non-LMS finance
source used to prove cross-product orchestration. Identity Platform is the first compliance/security
source used to prove a reusable subject and access-risk foundation. CRM Sales is the first
customer-domain source used to prove Customer 360 and account-health orchestration. Support Platform
is the first customer experience source used to prove support SLA and service journey intelligence.
Billing Platform is the first finance source of truth for certified daily revenue aggregates.
LMS remains a pilot slice, not the boundary of the platform.

## Mission

Build a production-ready, enterprise-grade data platform for the group:

- Keep OLTP service databases protected from BI, ad-hoc analytics and ML training workloads.
- Onboard product source systems through versioned contracts, CDC, outbox streams or governed batch
  connectors.
- Publish governed Bronze, Silver and Gold data products with ownership, contracts, lineage and SLOs.
- Support BI, finance/reconciliation, Customer 360, workforce analytics, product analytics, risk,
  compliance, ML feature stores and reverse ETL from trusted analytical layers.
- Make every pipeline reproducible, observable, idempotent and auditable.

The scope decision is captured in
[`docs/architecture/enterprise-data-platform-charter.md`](docs/architecture/enterprise-data-platform-charter.md):
`dp/` is the corporation's reusable data platform. LMS examples are pilot evidence, not platform
identity.

## Current Decision

The selected target architecture is an open lakehouse with Medallion layers and Data Mesh ownership:

```text
Enterprise products + SaaS + UI/event collectors
  -> Kafka / outbox / Debezium / batch connectors
  -> Bronze raw lakehouse tables
  -> Silver conformed enterprise/domain tables with PII controls
  -> Gold marts, semantic datasets and feature datasets
  -> BI, semantic metrics, ML, reverse ETL and data apps
```

The first implementation paths are deliberately narrow but reusable across products:

1. Register CourseFlow LMS under `products/lms-courseflow/`.
2. Ingest enrollment, course, gradebook and recommendation events.
3. Build Bronze event lake on object storage.
4. Build Silver learner activity and enterprise-ready common dimensions.
5. Build Gold recommendation interaction dataset and learner success mart.
6. Register Enterprise Commerce under `products/enterprise-commerce/`.
7. Build a finance benefit reconciliation slice from settlement events to Silver transactions and
   Gold reconciliation evidence.
8. Register Identity Platform under `products/identity-platform/`.
9. Build identity subject and access-risk governance from subject lifecycle events.
10. Register CRM Sales under `products/crm-sales/`.
11. Build customer identity links and Customer 360 account-health profiles from tokenized account events.
12. Register Support Platform under `products/support-platform/`.
13. Build support case state and daily SLA intelligence from metadata-only service events.
14. Register Billing Platform under `products/billing-platform/`.
15. Build finance billing transactions and certified daily revenue aggregates from settlement events.
16. Materialize Enterprise KPI Scorecard outputs from governed semantic metric snapshots across
    finance, customer, support, identity, recommendation and Control Tower Gold products.
17. Apply data quality, freshness metrics, catalog metadata and access policy from day one.

## Current Partner Review Status

`dp/` should now be described as an enterprise data-platform control plane plus local reference data
plane. It is ready for partner review of architecture, contracts, governance, evidence model,
Control Tower gates and executable local slices. It is not yet a live production data platform.

The current strongest local review path is:

```bash
cd dp
make ci
```

`make ci` runs repository validation, the Python test suite, the finance data-plane smoke, the live
Apicurio schema-registry runtime smoke, the live Redpanda event-backbone smoke with multi-partition
consumer-group evidence, the local Redpanda broker ACL smoke, the local Postgres transactional
outbox to Redpanda to Bronze preflight, the live source-Postgres-outbox to Redpanda to Bronze
Iceberg/MinIO smoke with Trino read-back, the live Parquet/DuckDB lakehouse smoke, the local
PyIceberg catalog smoke, the live MinIO object-store commit smoke, the live Trino SQL runtime smoke,
the live Trino Iceberg/MinIO smoke, the local Bronze-Iceberg-to-Silver/Gold-Iceberg orchestrated
publication smoke with Trino read-back and release activation evidence, the live Trino quality/SLO
gate over the published finance Gold Iceberg table, the local Trino runtime security smoke, the
local Dagster orchestration smoke, the local Dagster Day-2 smoke for
retry/tick/backfill evidence, the portfolio release smoke and the production review pack with
portfolio plus live schema
registry/event-backbone/broker-ACL/transactional-outbox/live-Bronze-ingestion/orchestrated-publication/live-quality-SLO/lakehouse/Iceberg/object-store/Trino/security/Dagster
evidence attached. The review pack intentionally separates three verdicts:

- `partner_review_ready=true`: the evidence pack is complete enough for partner review.
- `code_control_plane_ready_excluding_live_infra=true`: non-infrastructure Control Tower blockers
  are clear in the generated artifact.
- `production_ready=false`: live-runtime/capability evidence is still required before production
  signoff.

The current portfolio smoke covers all 12 Gold outputs, activates the P0 local source evidence path
for the remaining P0 sources, and leaves Control Tower blockers only in live capability/runtime
maturity gates. The live lakehouse smoke moves the finance slice from JSONL-only into real Parquet
storage and DuckDB SQL query execution. The PyIceberg catalog smoke commits Bronze/Silver/Gold tables
into a real local Iceberg SQL catalog and verifies snapshot metadata plus table scan read-back. The
object-store commit smoke uploads those Bronze/Silver/Gold Parquet commits to a live MinIO
S3-compatible bucket, enforces a local SSE-S3 bucket policy, proves unencrypted PUT is denied,
proves encrypted PUT is allowed and verifies head/get read-back, hash, schema, row-count and
encryption-header evidence. The Trino SQL runtime smoke loads the finance Gold rows into a live
Trino memory catalog and verifies the aggregate query probe through Trino. The Trino Iceberg/MinIO
smoke creates and queries a Trino Iceberg table backed by MinIO through a local Postgres JDBC
catalog, then verifies Iceberg `$snapshots` and `$files` metadata plus MinIO data/metadata objects
with SSE-S3 headers. The orchestrated publication smoke reads the live Bronze finance Iceberg table,
builds Silver and Gold finance reconciliation through the existing pipeline logic, writes Silver and
Gold back to Iceberg, verifies both tables through Trino, and generates release evidence, promotion,
activation, rollback pointer and active-pointer drift-negative evidence through a local Dagster
in-process run. The live quality/SLO smoke queries that published Gold Iceberg table through Trino,
emits non-synthetic `quality_runtime_evidence.v1`, green `slo_alert_evidence.v1`, a
`quality_slo_release_gates_ops_report.v1` and negative controls for corrupt Gold, stale freshness,
red alert state, environment mismatch and missing production-like alert evidence. The Trino runtime
security smoke force
recreates Trino with file-based access-control rules, proves `dp_allowed` can read the governed
Iceberg table, proves the same user cannot write, and proves `dp_denied` plus an unknown user are
blocked with runtime `Access Denied` decisions. The Dagster orchestration smoke runs a real local
Dagster job over the finance live/object-store/Trino evidence and reads back run history plus event
logs. The Dagster Day-2 smoke adds local retry event, schedule tick ledger and backfill partition
materialization evidence, but it is intentionally not used to close production daemon, distributed
executor or managed backfill P0 blockers. This keeps the artifact honest: DP can be reviewed now,
but production signoff still needs production Debezium/Kafka Connect or outbox-relay deployment
evidence, connector HA and secret rotation, production catalog HA/concurrency, cross-engine commit
compatibility beyond the local Trino/PyIceberg proof, production cloud KMS key rotation and external
bucket-policy attestation, managed quality runner/exporter rollout, production Alertmanager/PagerDuty
route evidence, production authn/service identity, row/column masking, centralized audit, Dagster
daemon/schedule/distributed-executor/backfill/HA
evidence and the remaining P0 capability maturity uplift.

## Folder Layout

| Path | Purpose |
|---|---|
| `contracts/` | Event envelope, topic contracts, data product contract templates and compatibility rules. |
| `products/` | Product onboarding boundary. CourseFlow LMS, Enterprise Commerce, Billing Platform, Identity Platform, CRM Sales, Support Platform and Enterprise Data Platform are the first product examples. |
| `domains/` | Enterprise Data Mesh domain ownership and cross-product business semantics. |
| `use-cases/` | Group-wide PO/BA use-case and data-product portfolio registry. |
| `platform/` | Shared ingestion, lakehouse, processing, orchestration, quality, governance, security, serving and ops capabilities. |
| `platform/capabilities/` | Enterprise capability maturity registry, reference-model mapping and production readiness report inputs. |
| `platform/control-tower/` | Data Product Control Tower operating model, P0 blocker taxonomy and report contract. |
| `catalog/` | Metadata-as-code guidance for glossary, ownership, discovery and lineage registration. |
| `governance/` | Enterprise governance model, domain council rules and policy ownership. |
| `templates/` | Scaffolds for new products, domains and data products. |
| `docs/` | Architecture, ADRs, structure reviews, team operating model, roadmap and BA/PO use cases. |
| `src/enterprise_dp/` | Developer tooling for contract and structure validation. |
| `tests/` | Automated checks for platform tooling, contracts and local pipeline skeletons. |

## Implemented Now

- Contract validator CLI: `enterprise_dp.cli`.
- Product onboarding scaffold CLI: `enterprise-dp product-scaffold`.
- Local Bronze ingestion preflight CLI: `enterprise-dp ingest-bronze`.
- Local catalog/lineage export CLI: `enterprise-dp catalog-export`.
- OpenLineage-style runtime event export CLI: `enterprise-dp openlineage-export`.
- Observability and cost-attribution metrics export CLI: `enterprise-dp observability-export`.
- Catalog publish manifest CLI: `enterprise-dp catalog-publish-manifest` for DataHub/OpenMetadata
  publish evidence.
- Catalog lineage operations report CLI: `enterprise-dp catalog-lineage-ops-report`; it audits
  catalog bundle hash, publish manifest, OpenLineage JSONL validity, publish receipt evidence and
  per-product lineage coverage. Control Tower consumes `catalog_lineage_ops_report.v1` as a P0 gate,
  and the production review pack only removes the `catalog-lineage-control-plane` blocker when a
  staging/prod report is `production_like_ready`, runtime-attested and hash-bound to publish
  manifest, publish receipt and OpenLineage evidence. Local preflight evidence remains supporting
  evidence only.
- Ed25519 external evidence attestation verification with metadata-as-code trust key registry.
- Local schema registry compatibility report CLI: `enterprise-dp schema-registry-check`.
- Schema registry operations report CLI: `enterprise-dp schema-registry-ops-report`; it audits
  local compatibility, production publication evidence, producer schema-id enforcement evidence,
  broker-enforced validation evidence and signed external attestation. Control Tower consumes
  `schema_registry_ops_report.v1` as a P0 schema compatibility gate.
- Local schema registry runtime smoke CLI: `enterprise-dp schema-registry-runtime-smoke`; it starts
  local Apicurio Registry, publishes every topic payload JSON Schema through the
  Confluent-compatible v7 API, applies subject compatibility, reads each schema back and verifies the
  registered hash matches the repository contract. It writes
  `schema_registry_runtime_smoke_report.v1` and is part of `make ci`. This proves local live registry
  publication/read-back, not production registry auth/RBAC, HA storage, producer schema-id
  enforcement or broker-enforced validation.
- Schema registry publication attestation CLI: `enterprise-dp schema-registry-attestation`; it signs
  the runtime smoke `schema_registry_publication_manifest.v1` with Ed25519, verifies it against
  `platform/security/evidence-trust-keys.yaml`, and binds `subject_hash` to the publication manifest
  hash from `schema_registry_runtime_smoke_report.v1`. `make ci` emits
  `external_evidence_attestation.v1` for the local schema registry slice and the production review
  pack removes `external_attestation_for_production_registry` only when the signature, key scope and
  subject hash all verify. This does not claim production KMS/HSM custody, key rotation, timestamp
  authority, external auditor signing, registry auth/RBAC or HA storage.
- Schema registry auth smoke CLI: `enterprise-dp schema-registry-auth-smoke`; it starts a local
  token/RBAC gateway in front of Apicurio, proves publisher publish/config/read succeeds, proves
  reader write is denied, proves missing/unknown/denied tokens are rejected, and writes
  authorization audit events without persisting token values. `make ci` emits
  `schema_registry_auth_smoke_report.v1`; the production review pack removes
  `production_registry_authentication_authorization` only when these allow/deny probes and audit
  evidence all pass. This is local production-style auth evidence, not enterprise OIDC/Keycloak,
  secret rotation, external WAF/API gateway or registry HA storage.
- Schema registry storage smoke CLI: `enterprise-dp schema-registry-storage-smoke`; it runs two
  Apicurio SQL registry replicas over shared PostgreSQL storage, publishes/configures a subject
  through replica A, reads the exact schema hash and compatibility through replica B, restarts
  replica A and verifies durable read-back. `make ci` emits
  `schema_registry_storage_smoke_report.v1`; Docker env-files are created in an OS temp directory
  and deleted after container startup, so the uploaded build artifact keeps only redacted command
  evidence. The production review pack removes
  `production_registry_ha_storage` only when shared SQL storage, cross-replica read-after-write and
  replica restart read-back all pass. This does not claim managed HA Postgres, multi-AZ deployment,
  load-balancer failover, backup/restore/PITR or database migration runbooks.
- Contract impact report CLI: `enterprise-dp contract-impact-report`; it joins schema compatibility
  with catalog lineage to identify affected Bronze/Silver/Gold data products, P0/P1 use cases,
  active grants, required approvals and the release decision for a topic contract change.
- Local access-policy evidence CLI: `enterprise-dp access-policy-check`.
- Access grant operations report CLI: `enterprise-dp access-grant-ops-report`; it audits the
  group-wide access grant registry for expired active grants, missing approvals, maker-checker
  conflicts, review-overdue grants, expiring grants, PII export exceptions and consumer-contract
  control drift.
- Enterprise change-control evidence CLI: `enterprise-dp change-control-check` over
  `governance/change-requests.yaml` for source onboarding, schema changes, access grants, catalog
  publish and Gold data product release approvals.
- Local pipeline runner registry CLI: `enterprise-dp pipeline-list`, `enterprise-dp pipeline-describe`
  and `enterprise-dp run-pipeline`.
- Generic use-case orchestration CLI: `enterprise-dp run-use-case`, driven by
  `use-cases/registry.yaml` implementation metadata.
- Local data-plane smoke CLI: `enterprise-dp data-plane-smoke`; the default finance
  reconciliation slice runs contracted source events through Bronze, Silver, Gold, catalog,
  release-gate evidence and a Gold query probe, then writes `data_plane_smoke_report.v1` with file
  hashes, row counts and failed-check details for CI review. This is a local CI data-flow gate, not
  a replacement for live Kafka/Iceberg/Trino production runtime evidence.
- Local live lakehouse smoke CLI: `enterprise-dp live-lakehouse-smoke`; it takes the finance slice
  beyond JSONL by writing Bronze/Silver/Gold Parquet table commits with PyArrow and executing the
  Gold query probe through DuckDB SQL. It writes `live_lakehouse_smoke_report.v1` and is part of
  `make ci`. This proves real local storage/query execution, while still explicitly leaving Iceberg
  MinIO-backed Iceberg warehouse, Trino Iceberg/MinIO federated query runtime, production
  orchestrator daemon/backfill history and production security enforcement as open production gaps.
- Local PyIceberg catalog smoke CLI: `enterprise-dp iceberg-catalog-smoke`; it starts from the
  finance live lakehouse Parquet commits, creates a local PyIceberg SQL catalog, commits
  Bronze/Silver/Gold Iceberg tables, verifies snapshot metadata files and scans each table back. It
  writes `iceberg_catalog_smoke_report.v1` and is part of `make ci`. This proves Iceberg table and
  catalog commit mechanics locally, not a MinIO-backed Iceberg warehouse, REST/Nessie/Hive catalog
  service or Trino Iceberg connector.
- Local object-store commit smoke CLI: `enterprise-dp object-store-commit-smoke`; it starts from the
  finance live lakehouse Parquet commits, uploads Bronze/Silver/Gold objects to a live MinIO
  S3-compatible bucket, configures default SSE-S3 encryption, applies a deny policy for unencrypted
  writes, verifies encrypted writes are allowed, verifies object metadata, downloads the objects back
  and checks hash, row count and schema fingerprints with PyArrow. It writes
  `object_store_commit_smoke_report.v1` and is part of `make ci`. This is still a local
  object-store commit/encryption proof, not cloud KMS rotation, external bucket-policy attestation,
  an Iceberg catalog snapshot or Trino Iceberg/MinIO federated query proof.
- Local Trino SQL runtime smoke CLI: `enterprise-dp trino-sql-runtime-smoke`; it starts local Trino,
  loads the finance Gold reconciliation rows into the Trino `memory` catalog and executes the same
  reconciliation aggregate probe through Trino SQL. It writes `trino_sql_runtime_smoke_report.v1` and
  is part of `make ci`. This is a Trino engine/runtime proof, not a Trino Iceberg connector or
  MinIO-backed federated lakehouse query proof.
- Local Trino Iceberg/MinIO smoke CLI: `enterprise-dp trino-iceberg-minio-smoke`; it starts local
  MinIO, Postgres JDBC catalog and Trino with the Iceberg connector, creates a finance Gold Iceberg
  table in a MinIO-backed warehouse, inserts the finance Gold rows, executes the reconciliation
  aggregate probe through Trino, queries Iceberg `$snapshots` and `$files`, and verifies MinIO data
  plus metadata objects with SSE-S3 headers. It writes `trino_iceberg_minio_smoke_report.v1` and is
  part of `make ci`. This proves local Trino Iceberg/MinIO federation plus local object-store
  encryption enforcement, not production catalog HA/concurrency, managed multi-engine failover,
  cloud KMS rotation, external bucket-policy attestation or production security enforcement.
- Local catalog cross-engine smoke CLI: `enterprise-dp catalog-cross-engine-smoke`; it reuses the
  same local MinIO, Postgres JDBC catalog and Trino stack, creates an Iceberg table through Trino,
  reads it through PyIceberg, appends through PyIceberg, verifies Trino can read the new snapshot and
  verifies a stale PyIceberg handle cannot overwrite the latest snapshot. It writes
  `catalog_cross_engine_smoke_report.v1` and is part of `make ci`. This closes the local
  `cross_engine_commit_compatibility` evidence gap for review packs, but it is still not production
  catalog HA, managed failover, backup/restore/PITR or multi-AZ locking evidence.
- Production catalog runtime ops CLI: `enterprise-dp catalog-runtime-ops-report`; it consumes a
  real staging/prod `managed_catalog_runtime_evidence.v1` export or external attestation and writes
  `catalog_runtime_ops_report.v1`. The gate is fail-closed unless the evidence is production-like,
  non-synthetic, redacted, hash-bound to release/change-ticket/warehouse/service identity/upstream
  evidence, and proves multi-AZ catalog HA, managed failover, read/write after failover, stale
  commit rejection, lost-update prevention, backup/restore/PITR, clean audit and external
  attestation. Local evidence never closes production catalog runtime gaps.
- Local Trino runtime security smoke CLI: `enterprise-dp trino-runtime-security-smoke`; it starts the
  local MinIO/Postgres/Trino stack, force recreates Trino so file-based access-control rules are
  loaded, checks explicit `--user` identities, verifies an allowed read on the governed Iceberg Gold
  table, verifies write denial for the read-only user, verifies select denial for a denied user and
  verifies default-deny for an unknown user. It also creates a small Iceberg security probe table and
  verifies local Trino row-level filtering plus column masking through file-based access-control
  rules. The smoke writes structured runtime security audit events to a local JSONL audit sink and
  attaches a manifest proving every expected allow/deny/filter/mask decision was persisted. It writes
  `trino_runtime_security_smoke_report.v1` and is part of `make ci`. This proves local Trino
  authorization, row-filter, mask and audit-sink evidence, not production OIDC/Keycloak
  authentication, production SIEM/audit pipeline or production policy bundle distribution.
- Local OPA policy-decision smoke CLI: `enterprise-dp policy-decision-smoke`; it starts a real OPA
  server, loads a local Rego policy, verifies allow/deny decisions, row-filter and column-mask
  decisions, verifies policy-admin maker-checker approval, blocks self-approval and missing evidence,
  and writes a structured policy-decision audit sink. It writes `policy_decision_smoke_report.v1` and
  is part of `make ci`. This proves local OPA PDP and policy-admin maker-checker evidence, not
  production OIDC/Keycloak, HA OPA/Ranger clusters, signed bundle distribution, SIEM export or
  production secret rotation.
- Local OIDC auth smoke CLI: `enterprise-dp oidc-auth-smoke`; it creates a local OIDC-compatible
  issuer/JWKS, signs RS256 access tokens, verifies issuer, audience, expiry, signature, unknown `kid`,
  missing-token and missing-role denial behavior, then writes a structured authn audit sink with token
  hashes instead of raw access tokens. It writes `oidc_auth_smoke_report.v1` and is part of `make ci`.
  This proves local OIDC/JWKS validation evidence for the runtime boundary, not enterprise Keycloak
  realm deployment, group sync, managed IdP HA, JWKS rotation from a managed provider or production
  secret rotation.
- Access/privacy release gate: the production review pack now treats `trino_runtime_security_smoke_report.v1`
  + `policy_decision_smoke_report.v1` + `oidc_auth_smoke_report.v1` as one strict combined gate. Only
  when Trino proves runtime allow/deny, row filters, column masks and audit, OPA proves policy
  decisions plus maker-checker, and OIDC proves signed-token validation plus denial controls does the
  pack remove the P0 `access-privacy-enforcement` capability blocker. This does not remove production
  secret rotation, HA PDP/Keycloak, signed policy bundle distribution, SIEM export or managed IdP
  operation blockers.
- Local secret-rotation smoke CLI: `enterprise-dp secret-rotation-smoke`; it creates a local encrypted
  versioned secret store, rotates runtime secret versions from v1 to v2, verifies old-version revoke,
  verifies service-identity-scoped reads, denies unauthorized and missing-secret reads, and writes a
  Dagster service-identity injection manifest with only a secret handle/version/hash and redacted
  value. It writes `secret_rotation_smoke_report.v1` and is part of `make ci`. This proves local
  secret rotation workflow and orchestrator service-identity injection evidence, not managed
  secret-manager HA, cloud KMS/HSM custody, workload identity federation, CSI/ESO injection,
  automatic rotation scheduling, SIEM export or production secret rotation signoff.
- Secret rotation operations report CLI: `enterprise-dp secret-rotation-ops-report`; it consumes
  managed `managed_secret_rotation_evidence.v1` from staging/prod, checks every P0 runtime service
  in `platform/runtime/topology.yaml` for external secret handles, service identity, active secret
  version, KMS key hash, rotation policy, old-version revoke/deny, unauthorized/missing-secret deny
  and plaintext absence, then validates managed secret-manager HA, workload identity federation,
  KMS/HSM custody, SIEM audit export and external attestation. The production review pack removes
  `production_secret_rotation`, `production_cloud_kms_key_rotation` and related secret/KMS runtime
  blockers only when this report is production-like and strict-passing.
- Local Dagster orchestration smoke CLI: `enterprise-dp dagster-orchestration-smoke`; it runs a real
  Dagster in-process job over the finance live lakehouse, object-store and Trino smoke evidence,
  records the Dagster run ID, reads back the Dagster event log and writes
  `dagster_orchestration_smoke_report.v1`. It is part of `make ci`. This proves local Dagster run
  history, not production daemon scheduling, distributed execution, backfill history or service
  identity enforcement.
- Local Dagster Day-2 smoke CLI: `enterprise-dp dagster-day2-smoke`; it runs a real local Dagster
  retry probe, writes a schedule tick ledger tied to the run ID, materializes backfill partitions and
  writes `dagster_day2_smoke_report.v1`. It is part of `make ci` and can be attached to the
  production review pack. The review pack treats it as a strict release gate only when retry/restart
  events, positive retry backoff, schedule tick history, backfill partition materialization history
  and zero failed checks are all present. This proves local retry/tick/materialization evidence, not
  production Dagster daemon HA, distributed or Kubernetes run launchers, managed run storage,
  production backfill scheduling or orchestrator metrics export.
- Production orchestration runtime ops CLI: `enterprise-dp orchestration-runtime-ops-report`; it
  consumes a staging/prod `managed_orchestration_runtime_evidence.v1` artifact and writes
  `orchestration_runtime_ops_report.v1`. The strict gate requires production-like, redacted,
  fresh and externally attested evidence with release/change binding, git SHA, image digest,
  Dagster service identity, daemon/scheduler/worker HA, distributed executor or Kubernetes run
  launcher, managed run storage, schedule tick history, retry/backoff history, backfill
  materialization history, service-identity/secret-injection evidence, metrics/alerts, audit and
  binding hashes. Local or sample evidence never closes production orchestration runtime gaps.
- Local event-backbone smoke CLI: `enterprise-dp event-backbone-smoke`; it starts local Redpanda,
  produces finance sample events, consumes them back, writes `event_backbone_smoke_report.v1` and
  feeds the consumed records into the data-plane smoke. It then round-trips every P0 source with a
  registered `evidence.localSamplePath` through local Redpanda, normalizing bridge-required sources
  before produce, stamping producer records with schema IDs resolved from the local Apicurio runtime
  report when it is available, and validating consumed records against the canonical topic
  envelope/payload schemas. It also creates a local three-partition Redpanda topic, produces records
  directly to every partition, consumes them through a consumer group and verifies group lag returns
  to zero across all partitions.
  It writes
  `ingestion_runtime_evidence.v1`, `ingestion_runtime_evidence_manifest.v1` and
  `event_cdc_ingestion_runtime_report.v1` for the local P0 source set so Control Tower can
  consume runtime ingestion evidence instead of relying only on a standalone smoke. It is part of
  `make ci`, so local and GitHub CI review packs carry the same live event-backbone and ingestion
  runtime evidence. This proves local Redpanda runtime coverage plus producer-side schema-id guard
  evidence, sink-side schema validation and multi-partition consumer-group lag-zero evidence for the
  registered P0 source samples, not Kafka Connect/Debezium, production DLT policy or broker-enforced
  validation.
- Local broker ACL smoke CLI: `enterprise-dp broker-acl-smoke`; it starts an isolated Redpanda
  container with a generated SASL/SCRAM listener config, creates an admin superuser plus allowed and
  denied client users, enables broker authorization, creates topic/group ACLs only for the allowed
  principal, proves the allowed user can produce and proves the denied user receives a broker
  authorization failure. It writes `broker_acl_smoke_report.v1` and is part of `make ci`. This
  closes the local `broker_acl_enforcement` evidence gap for the event backbone, not production mTLS,
  production secret rotation or production broker audit-log export.
- Local transactional outbox smoke CLI: `enterprise-dp transactional-outbox-smoke`; it starts local
  Postgres plus Redpanda, seeds the registered finance `transactional_outbox` source into a real
outbox table, polls the outbox rows through a local connector loop, publishes those records to
Redpanda, consumes them back and runs Bronze ingestion from the consumed records. It writes
`transactional_outbox_smoke_report.v1` and is part of `make ci`. This closes the local
`debezium_or_transactional_outbox_source_connector` evidence gap for the finance source path, not
production Debezium/Kafka Connect runtime, connector HA, deployed outbox relay or connector secret
rotation.
- Local live Bronze ingestion smoke CLI: `enterprise-dp live-bronze-ingestion-smoke`; it starts local
  source Postgres, Redpanda, MinIO, the Iceberg JDBC catalog and Trino, seeds the registered finance
  outbox source, publishes and consumes records with topic/partition/offset evidence, writes approved
  records into a Bronze Iceberg table through PyIceberg, reads the table back through Trino, verifies
  Iceberg snapshots/files, skips duplicate events idempotently, quarantines an invalid-schema record
  and proves restart resume from the offset ledger. It writes
  `live_bronze_ingestion_runtime_report.v1` and is part of `make ci`. This closes the local
  source-to-Bronze runtime proof for the finance benefit source, not production connector HA, secret
  rotation, backpressure policy or multi-source production rollout.
- Local orchestrated publication smoke CLI: `enterprise-dp orchestrated-publication-smoke`; it reads
  the finance Bronze Iceberg table produced by the live Bronze smoke, builds Silver and Gold through
  the finance reconciliation pipeline, writes both tables into the local MinIO-backed Iceberg
  warehouse, queries both tables through Trino, and generates release evidence, promotion,
  activation, rollback pointer, publication-ops and active-pointer drift-negative evidence from a
  local Dagster in-process run. It writes `orchestrated_live_publication_report.v1` and is part of
  `make ci`. This closes the local `silver-gold-publication` capability proof, not Dagster daemon,
  distributed executor, production retry/backfill policy, production catalog HA/concurrency or
  production secret rotation.
- Local live quality/SLO smoke CLI: `enterprise-dp live-quality-slo-smoke`; it reads the published
  finance Gold Iceberg table from the orchestrated publication report, queries runtime quality and
  freshness metrics through Trino, emits `quality_runtime_evidence.v1`, `slo_alert_evidence.v1` and
  `quality_slo_release_gates_ops_report.v1`, then runs negative controls for corrupt Gold, stale
  freshness, red alert state, environment mismatch and missing production-like alert evidence. It
  writes `live_quality_slo_smoke_report.v1` and is part of `make ci`. This closes the local
  `quality-slo-release-gates` capability proof for the finance Gold slice, not managed
  Great Expectations/Soda/dbt runner rollout, production Alertmanager/PagerDuty routing,
  multi-product runtime-quality rollout or production burn-rate monitoring.
- Portfolio release smoke CLI: `enterprise-dp portfolio-release-smoke`; it runs the implemented
  local use-case runners, writes passing release evidence for the current Gold portfolio, generates
  OpenLineage/catalog/quality ops artifacts and a Control Tower report with that evidence attached.
- Production review pack CLI: `enterprise-dp production-review-pack`; it generates a
  partner-review artifact set with data-plane smoke, live lakehouse smoke, runtime readiness,
  capability maturity and Control Tower evidence plus `production_review_pack.v1`. It can attach
  optional `portfolio_release_smoke_report.v1`, `live_lakehouse_smoke_report.v1`,
  `iceberg_catalog_smoke_report.v1`, `object_store_commit_smoke_report.v1`,
  `trino_sql_runtime_smoke_report.v1`, `trino_iceberg_minio_smoke_report.v1`,
  `catalog_runtime_ops_report.v1`,
  `trino_runtime_security_smoke_report.v1`, `policy_decision_smoke_report.v1`,
  `oidc_auth_smoke_report.v1`, `secret_rotation_smoke_report.v1`,
  `dagster_orchestration_smoke_report.v1`,
  `broker_acl_smoke_report.v1`, `transactional_outbox_smoke_report.v1`,
  `live_bronze_ingestion_runtime_report.v1`,
  `orchestrated_live_publication_report.v1`, `live_quality_slo_smoke_report.v1`,
  `catalog_lineage_ops_report.v1`, `semantic_metric_serving_ops_report.v1`,
  `source_activation_ops_report.v1`, `event_backbone_smoke_report.v1` and
  `event_cdc_ingestion_runtime_report.v1`; if any report is absent or failed, the pack records the
  gap in the P0 backlog. When ingestion runtime evidence
  covers fewer running connectors than
  registered P0 sources, the pack keeps
  `ingestion_runtime_p0_coverage_incomplete`; the default local CI smoke now covers the registered
  P0 source samples. The pack is review-ready even when the verdict correctly remains
  `production_ready=false`.
- Release promotion and activation manifest CLIs: `enterprise-dp release-promote` and
  `enterprise-dp release-activate`; activation writes the active pointer state for the approved
  data-product snapshot.
- Local P0 recommendation slice orchestration CLI: `enterprise-dp run-recommendation-slice`
  remains as the backward-compatible pilot command.
- Group-wide use-case portfolio registry: `use-cases/registry.yaml`.
- Initial event envelope schema: `contracts/event-envelope.v1.schema.json`.
- Enterprise metadata guardrails for product, domain owner, steward, residency, consumer contract and
  access personas.
- CourseFlow LMS P0 topic contracts for recommendation, enrollment, course publication and final grade
  events.
- Initial CourseFlow LMS data product contracts:
  - `bronze.events_recommendation_tracking`
  - `bronze.events_enrollment_completed`
  - `bronze.events_course_published`
  - `bronze.events_gradebook_final_grade_updated`
  - `silver.learner_activity`
  - `gold.recsys_interactions`
- Initial Enterprise Commerce finance contracts:
  - `bronze.events_benefit_settled`
  - `silver.finance_benefit_transactions`
  - `gold.finance_benefit_reconciliation`
- Initial Billing Platform revenue contracts:
  - `bronze.events_billing_transaction_settled`
  - `silver.finance_billing_transactions`
  - `gold.finance_revenue_daily`
- Initial Identity Platform compliance contracts:
  - `bronze.events_identity_subject_changed`
  - `silver.identity_subject`
  - `gold.access_risk_daily`
- Initial CRM Sales customer contracts:
  - `bronze.events_customer_account_changed`
  - `silver.customer_identity_link`
  - `gold.customer_360_profile`
- Initial Support Platform customer experience contracts:
  - `bronze.events_support_case_changed`
  - `silver.support_case`
  - `gold.support_sla_daily`
- Initial Enterprise Reporting scorecard contracts:
  - `gold.enterprise_kpi_daily`
  - `gold.executive_scorecard_daily`
- Product onboarding folders for CourseFlow LMS, Enterprise Commerce, Billing Platform, Identity
  Platform, CRM Sales, Support Platform, HRIS Workforce and Enterprise Data Platform.
- Product-level governance onboarding controls for privacy, retention, access, catalog lineage and
  release evidence defaults.
- Product-agnostic source bridge preflight CLI: `enterprise-dp source-bridge-normalize`; it converts
  registered raw source JSONL into canonical enterprise event envelopes before Bronze ingestion. The
  first adapters cover CourseFlow LMS P0 sources, while the framework is shared for any future
  enterprise product source that cannot publish the canonical envelope directly.
- Enterprise data change-control registry for maker-checker request workflow, risk rating, target
  environment, approvals, evidence and rollback or impact controls across products and domains.
- Scope guardrail policy and validator that prevent unreviewed pilot-product identity from leaking
  into shared platform code and docs.
- Environment manifests and validator for local/staging/prod P0 runtime capabilities, evidence mode
  and required stack components.
- Runtime/IaC topology-as-code under `platform/runtime/` with local compose skeleton,
  staging/prod OpenTofu skeletons, Dremio/TiDB phase gates and `enterprise-dp
  runtime-readiness-check` evidence reports. Production-like reports can consume machine-readable
  plan/apply/drift/backup/DR/health evidence produced or normalized by `enterprise-dp
  runtime-evidence-pack`; local can pass developer preflight, while staging/prod remain not-ready
  until valid live evidence is attached. `enterprise-dp production-review-pack` can now consume
  either a prebuilt `runtime_readiness_report.v1` or the raw plan/apply/drift/backup/health/DR
  evidence paths and removes the `platform-runtime-iac` capability blocker only when the resulting
  staging/prod readiness report is strict-passing and production-like.
- Source registry and validator for product source onboarding, canonical topic bridges, schema
  subjects, Bronze targets, privacy handling and production evidence requirements.
- Schema registry production governance CLI: `enterprise-dp schema-registry-ops-report`; local can
  use repository compatibility preflight and local Apicurio runtime smoke, while staging/prod require
  registry publication evidence, producer/broker enforcement flags and a signed
  `external_evidence_attestation.v1`.
- Source-to-Bronze readiness report CLI: `enterprise-dp source-readiness-check`; it gates source
  activation with bridge manifest, ingestion, replay, schema, change-control, catalog and OpenLineage
  evidence.
- Source readiness bundle CLI: `enterprise-dp source-readiness-bundle`; it runs the repeatable
  source-to-Bronze evidence path end to end for direct-canonical or bridge-required sources so
  source promotion decisions can be reviewed from one artifact pack.
- Source activation ledger under `governance/source-activations.yaml`; portfolio readiness can use
  it as an evidence-backed overlay so static registry status stays honest while approved activation
  records provide `effective_status=production_ready` for the matching environment.
- Source activation CLI: `enterprise-dp source-activate`; it creates `source_activation_manifest.v1`
  from a passed source readiness bundle, computes hashes from the actual bundle/readiness/registry
  files, enforces maker-checker and change-request alignment, requires a passing
  `runtime_readiness_report.v1` for staging/prod activation, appends the activation ledger only when
  gates pass and writes a per-source active pointer for rollback/review.
- Source revocation CLI: `enterprise-dp source-revoke`; it appends a `revoked` activation event,
  requires an approved `source_activation_revoke` change request and overwrites the per-source active
  pointer with a tombstone so portfolio readiness blocks the source again without mutating history.
  Break-glass revocation can be explicitly enabled for a latest active ledger record whose active
  pointer is already missing; the manifest records the missing-pointer condition and still requires
  maker-checker, an approved revoke change request and revocation evidence.
- Source activation operations report CLI: `enterprise-dp source-activation-ops-report`; it audits
  activation ledger health, active-pointer consistency, expiry, registry hash drift and revocation
  state across registered enterprise sources. Control Tower consumes the same artifact as a P0 gate
  so unactivated P0 sources, invalid ledgers, pointer drift and expired/revoked activations cannot be
  hidden from production signoff. In staging/prod this report is fail-closed: `passed=false` if any
  P0 source is unactivated, not active, expired/revoked, missing runtime-readiness evidence, missing
  its active pointer, drifting from the source-registry hash or carrying unverifiable activation
  evidence. `readinessReportUri`, `evidenceBundleUri` and `runtimeReadinessReportUri` must resolve
  to artifacts whose hashes match the ledger; placeholder URIs such as `evidence://...` are counted
  under `evidence_integrity_issue_count` and block `runtime_attested` mode. Static
  `status: production_ready` in `platform/ingestion/source-registry.yaml` remains desired state only;
  it never replaces activation ledger, pointer and runtime evidence.
- Event/CDC ingestion runtime report CLI: `enterprise-dp ingestion-runtime-check`; it audits
  registered source connector evidence for running tasks, lag SLO, DLT coverage, backpressure and
  offset ledger hashes. Control Tower consumes `event_cdc_ingestion_runtime_report.v1` as a P0 gate,
  so P0 sources cannot be signed off while runtime evidence is missing, stale, synthetic or failing.
- Event/CDC runtime evidence normalizer CLI: `enterprise-dp ingestion-runtime-evidence-normalize`;
  it converts Kafka Connect/Debezium status, consumer lag, DLT, backpressure, broker topic/ACL and
  offset-ledger exports into `ingestion_runtime_evidence.v1` plus a manifest with input hashes and
  readiness args for CI/CD.
- Source offset ledger CLI: `enterprise-dp offset-ledger-record`; it records partition watermarks,
  replay idempotency, row-hash bindings and Iceberg snapshot evidence for Bronze commits.
- Bronze lakehouse operations report CLI: `enterprise-dp bronze-lakehouse-ops-report`; it audits
  P0 Bronze source offset ledgers, replay proof, Iceberg commit metadata, quarantine state,
  append-only enforcement and table maintenance evidence. Control Tower consumes
  `bronze_lakehouse_ops_report.v1` as a P0 gate.
- Lakehouse snapshot evidence CLI: `enterprise-dp snapshot-evidence-record`; it binds Silver/Gold
  pipeline outputs to Iceberg snapshot metadata, contract hashes, schema hashes, partition spec
  hashes, upstream offset ledger evidence and release/use-case/runner identity.
- Silver/Gold publication operations report CLI:
  `enterprise-dp silver-gold-publication-ops-report`; it audits release evidence, promotion
  manifests, activation manifests, active pointer state, rollback targets and production change
  tickets before serving-layer data products can be exposed. Control Tower consumes
  `silver_gold_publication_ops_report.v1` as a P0 gate.
- Quality/SLO release gates operations report CLI:
  `enterprise-dp quality-slo-release-gates-ops-report`; it audits quality profile coverage,
  release evidence quality/freshness gates, runtime quality evidence, freshness SLO state, alert
  evidence and incident/SLO state. Control Tower consumes
  `quality_slo_release_gates_ops_report.v1` as a P0 gate before production signoff.
- Backfill/replay readiness CLI: `enterprise-dp backfill-readiness-check`; it gates bounded
  production-like backfills with approved scope, dry-run, data-diff, source offset ledger,
  lakehouse snapshot evidence, change-control, rollback, impact and communication evidence.
  `production-review-pack` can attach this report and only removes the
  `backfill-change-governance` blocker when staging/prod readiness is `runtime_attested`, `ready`,
  passed and all required evidence references are local, hash-bound artifacts.
- Pipeline registry manifest and validator for runnable pipeline metadata, use-case bindings,
  input/output data products, evidence capabilities and implementation parity.
- Semantic metric registry and validator for governed finance, compliance/access-risk,
  recommendation and executive KPI definitions over approved Gold data products.
- Semantic metric certification workflow CLI:
  `enterprise-dp semantic-metric-certification-report`; it validates maker-checker certification,
  evidence, diff and impact analysis before a metric can be treated as certified.
- Semantic view manifest export CLI: `enterprise-dp semantic-views-export` for Trino/Dremio view SQL
  generated from the metric registry.
- Semantic metric serving operations report CLI:
  `enterprise-dp semantic-metric-serving-ops-report`; it audits semantic metric lifecycle,
  certification evidence, semantic view manifest validity, deployment smoke-test/access evidence and
  usage tracking evidence. Control Tower consumes `semantic_metric_serving_ops_report.v1` as a P0
  serving gate. The production review pack removes the `semantic-metric-serving` capability blocker
  only when a staging/prod report is `production_like_ready`, `runtime_attested`, has zero metric
  gaps and is backed by explicit semantic view manifest, certification, deployment and usage
  evidence. Local preflight evidence remains supporting evidence only.
- Schema registry operations report CLI: `enterprise-dp schema-registry-ops-report`; in local mode it
  validates compatibility and subject coverage as a preflight. In staging/prod mode it must attach a
  production-like publication manifest plus signed external attestation; every P0 subject must be
  registered with compatibility, schema/artifact id, matching payload hash, producer schema-id
  enforcement and broker/sink validation. The production review pack removes the
  `schema-registry-compatibility` capability blocker only when this production-like ops report is
  strict-passing.
- Enterprise capability maturity registry and report CLI: `enterprise-dp capability-maturity-report`;
  it shows which P0/P1 platform capabilities are still below production target maturity.
- Enterprise portfolio readiness report CLI: `enterprise-dp portfolio-readiness-report`; it joins
  product onboarding, use-case demand, first-slice contracts and source-readiness gaps into a PO/BA
  decision board for what enterprise product/use case should be implemented next. Pass
  `--source-activation-ledger governance/source-activations.yaml` when PO/SA want the board to honor
  approved source readiness activations.
- Data Product Control Tower report CLI: `enterprise-dp control-tower-report`; it aggregates
  catalog, quality, lineage, access, access-grant operations, source-activation operations,
  event/CDC ingestion runtime, Bronze lakehouse operations, Silver/Gold publication operations,
  Quality/SLO release gate operations, schema registry operations, data-plane smoke evidence,
  contract-impact reports, release evidence, runtime readiness and capability maturity into a P0
  production signoff decision report.
- Data incident/SLO report CLI: `enterprise-dp incident-report`; it converts Control Tower P0
  blockers into an operational incident queue with severity, owner, assignee, SLA age, runbook,
  linked evidence and page-now recommendations.
- Runnable use-case implementations:
  - `enterprise-revenue-intelligence`
  - `ml-feature-governance`
  - `finance-benefit-reconciliation`
  - `identity-access-governance`
  - `customer-account-health`
  - `customer-support-experience-intelligence`
  - `data-product-control-tower`
  - `enterprise-kpi-scorecard`
- P0 Data Product Control Tower use-case registration and Gold contracts:
  - `gold.data_product_inventory`
  - `gold.contract_compliance_daily`
  - `gold.quality_sla_daily`
  - `gold.lineage_coverage_daily`
  The local runner `control_tower.materialize_gold.from_report.v1` materializes these four Gold
  outputs from `data_product_control_tower_report.v1`.
- P0 Enterprise KPI Scorecard use-case registration and Gold contracts:
  - `gold.enterprise_kpi_daily`
  - `gold.executive_scorecard_daily`
  The local runner `enterprise_reporting.executive_scorecard.from_semantic_snapshot.v1`
  materializes non-PII executive KPI outputs from `semantic_metric_snapshot.v1`.
- Agent delivery model: `docs/team/agent-operating-model.md`.
- Reference model benchmark: `docs/architecture/reference-model-benchmark.md`.
- Enterprise use-case roadmap: `docs/architecture/enterprise-use-case-roadmap.md`.

Run local checks:

```bash
cd dp
make check
make data-plane-smoke
```

Live event-backbone smoke:

```bash
cd dp
make event-backbone-smoke
```

Live broker ACL smoke:

```bash
cd dp
make broker-acl-smoke
```

Live transactional outbox smoke:

```bash
cd dp
make transactional-outbox-smoke
```

Live source-to-Bronze Iceberg smoke:

```bash
cd dp
make live-bronze-ingestion-smoke
```

For the strict DP CI path used before partner review, run:

```bash
cd dp
make ci
```

This is the CI/CD gate wired into `.github/workflows/data-platform.yml`. It fails if validation,
tests, schema registry runtime smoke, Redpanda event-backbone smoke with multi-partition
consumer-group evidence, data-plane smoke, live lakehouse smoke, Iceberg catalog smoke, object-store
commit smoke, Trino SQL smoke, Trino Iceberg/MinIO smoke, Trino runtime security smoke, Redpanda
broker ACL smoke, Postgres transactional-outbox-to-Redpanda-to-Bronze preflight, live
source-Postgres-outbox-to-Redpanda-to-Bronze-Iceberg/MinIO smoke, Dagster orchestration smoke,
Bronze-to-Silver/Gold orchestrated publication smoke, live quality/SLO Gold gate smoke, Dagster
Day-2 smoke, portfolio release smoke or the production review pack cannot be generated.
The workflow also verifies review-pack verdicts with `enterprise-dp production-review-gate`: the
default CI path enforces `code-control-plane`, and a manual workflow input can enforce the stricter
`production-ready` profile. `production-review-pack` remains an artifact generator; the gate command
is the fail-closed verifier.

Managed runtime ops readiness has a separate fail-closed artifact lane:

```bash
cd dp
make production-ops-readiness-pack
```

This writes `catalog_runtime_ops_report.v1`, `orchestration_runtime_ops_report.v1` and
`secret_rotation_ops_report.v1` into `build/catalog-runtime-ops`,
`build/orchestration-runtime-ops` and `build/secret-rotation-ops`, then attaches them to
`build/managed-runtime-ops-review/production-review-pack.json`. By default no managed runtime
evidence is supplied, so the reports are expected to be red and the pack remains
`production_ready=false`. To attach real staging/prod evidence, pass
`CATALOG_RUNTIME_EVIDENCE`, `ORCHESTRATION_RUNTIME_EVIDENCE` and `SECRET_ROTATION_EVIDENCE`; local
or sample evidence still does not close production catalog, orchestration or KMS/secret-manager
blockers.

Source onboarding has its own release gate:

```bash
cd dp
make source-onboarding-release-gate
```

This target always writes `build/source-activation-ops/staging.json` first, even when the source
activation ops CLI returns non-zero, then attaches it to
`build/source-onboarding-review-pack/production-review-pack.json` and runs the
`source-onboarding` review gate. The default observation timestamp is
`SOURCE_ONBOARDING_AS_OF=2026-06-19T02:05:00Z`, after the Billing break-glass revocation. With the
current baseline it is expected to fail because staging has 8 P0 sources, 0 active P0 sources, 7
unactivated P0 sources and one revoked Billing source.
The previous Billing activation that referenced placeholder readiness/runtime evidence has been
revoked with a tombstone pointer, so pointer/runtime/evidence-integrity issue counts are expected to
stay at zero while the source-onboarding gate remains red for real activation coverage. That failure
is intentional production evidence, not a test flake.

For a partner-review Control Tower pack with the finance data-plane smoke evidence attached:

```bash
cd dp
make production-review-pack
```

For the stronger partner-review pack, attach multi-use-case release evidence:

```bash
cd dp
make portfolio-release-smoke
make production-review-pack PORTFOLIO_RELEASE_SMOKE_REPORT=build/portfolio-release-smoke/portfolio-release-smoke-report.json
```

When Docker is available, attach the live schema registry, object-store, Trino SQL, Dagster
orchestration, event-backbone and ingestion runtime evidence to the same pack:

```bash
cd dp
make schema-registry-runtime-smoke
make object-store-smoke
make iceberg-catalog-smoke
make trino-sql-smoke
make trino-iceberg-minio-smoke
make catalog-cross-engine-smoke
make trino-runtime-security-smoke
make policy-decision-smoke
make dagster-orchestration-smoke
make dagster-day2-smoke
make event-backbone-smoke
make broker-acl-smoke
make transactional-outbox-smoke
make live-bronze-ingestion-smoke
make orchestrated-publication-smoke
make live-quality-slo-smoke
make production-review-pack \
  PORTFOLIO_RELEASE_SMOKE_REPORT=build/portfolio-release-smoke/portfolio-release-smoke-report.json \
  SCHEMA_REGISTRY_RUNTIME_SMOKE_REPORT=build/schema-registry-runtime-smoke/schema-registry-runtime-smoke-report.json \
  LIVE_LAKEHOUSE_SMOKE_REPORT=build/live-lakehouse-smoke/live-lakehouse-smoke-report.json \
  ICEBERG_CATALOG_SMOKE_REPORT=build/iceberg-catalog-smoke/iceberg-catalog-smoke-report.json \
  OBJECT_STORE_SMOKE_REPORT=build/object-store-smoke/object-store-commit-smoke-report.json \
  TRINO_SQL_SMOKE_REPORT=build/trino-sql-smoke/trino-sql-runtime-smoke-report.json \
  TRINO_ICEBERG_MINIO_SMOKE_REPORT=build/trino-iceberg-minio-smoke/trino-iceberg-minio-smoke-report.json \
  CATALOG_CROSS_ENGINE_SMOKE_REPORT=build/catalog-cross-engine-smoke/catalog-cross-engine-smoke-report.json \
  TRINO_RUNTIME_SECURITY_SMOKE_REPORT=build/trino-runtime-security-smoke/trino-runtime-security-smoke-report.json \
  POLICY_DECISION_SMOKE_REPORT=build/policy-decision-smoke/policy-decision-smoke-report.json \
  DAGSTER_ORCHESTRATION_SMOKE_REPORT=build/dagster-orchestration-smoke/dagster-orchestration-smoke-report.json \
  DAGSTER_DAY2_SMOKE_REPORT=build/dagster-day2-smoke/dagster-day2-smoke-report.json \
  BROKER_ACL_SMOKE_REPORT=build/broker-acl-smoke/broker-acl-smoke-report.json \
  TRANSACTIONAL_OUTBOX_SMOKE_REPORT=build/transactional-outbox-smoke/transactional-outbox-smoke-report.json \
  LIVE_BRONZE_INGESTION_SMOKE_REPORT=build/live-bronze-ingestion-smoke/live-bronze-ingestion-smoke-report.json \
  ORCHESTRATED_PUBLICATION_SMOKE_REPORT=build/orchestrated-publication-smoke/orchestrated-publication-smoke-report.json \
  LIVE_QUALITY_SLO_SMOKE_REPORT=build/live-quality-slo-smoke/live-quality-slo-smoke-report.json \
  EVENT_BACKBONE_SMOKE_REPORT=build/event-backbone-smoke/event-backbone-smoke-report.json \
  CATALOG_LINEAGE_OPS_REPORT=build/evidence/catalog-lineage-ops-prod.json \
  SEMANTIC_METRIC_SERVING_OPS_REPORT=build/evidence/semantic-metric-serving-ops-prod.json \
  SOURCE_ACTIVATION_OPS_REPORT=build/evidence/source-activation-ops-prod.json \
  SECRET_ROTATION_OPS_REPORT=build/evidence/secret-rotation-ops-prod.json \
  INGESTION_RUNTIME_REPORT=build/event-backbone-smoke/ingestion-runtime/event-cdc-ingestion-runtime-report.json
```

The review pack writes `build/production-review-pack/production-review-pack.json` plus the supporting
evidence artifacts. It is expected to report `production_ready=false` while broader production P0
blockers still exist; that verdict is part of the artifact. If the event-backbone smoke is not
attached, the pack intentionally adds `event_backbone_smoke_not_attached` to the P0 gap backlog.
`make ci` attaches it by default. If ingestion runtime evidence is not attached, it adds
`ingestion_runtime_report_not_attached`; if the attached evidence covers fewer running connectors
than P0 sources, it keeps `ingestion_runtime_p0_coverage_incomplete`. The default local CI smoke now
also attaches `transactional_outbox_smoke_report.v1`; if it passes, the pack removes
`debezium_or_transactional_outbox_source_connector` from the event-backbone backlog while still
listing production Debezium/Kafka Connect, connector HA and secret-rotation gaps as out of scope for
the local smoke. The default local CI smoke also attaches
`live_bronze_ingestion_runtime_report.v1`; when it passes, the pack removes the
`event-cdc-ingestion-runtime` and `bronze-lakehouse-evidence` capability blockers for the finance
benefit source while still keeping source-onboarding, production connector HA, production
backpressure, production secret rotation and production catalog HA as explicit gaps. The default
local CI smoke also attaches `orchestrated_live_publication_report.v1`; when it passes, the pack
removes the `silver-gold-publication` capability blocker while still keeping Dagster
daemon/schedule, distributed executor, production retry/backfill policy, production catalog
HA/concurrency and production secret-rotation gaps. The default local CI smoke also attaches
`live_quality_slo_smoke_report.v1`; when it passes, the pack removes the
`quality-slo-release-gates` capability blocker while still keeping managed quality runner/exporter,
production Alertmanager/PagerDuty route, multi-product rollout and production burn-rate monitoring
outside the local proof. The default
event-backbone smoke round-trips the registered P0 source samples,
proves local multi-partition consumer-group lag-zero behavior and proves local broker ACL
authorization, so it should keep those coverage gaps absent while those samples remain current. If
the optional schema
registry runtime smoke is not attached, it adds `schema_registry_runtime_smoke_not_attached`.
When `schema_registry_publication_attestation.v1` is attached and verifies against the trust key
registry, the pack removes `external_attestation_for_production_registry` while still keeping
production registry auth/RBAC, HA storage, KMS/HSM custody, key rotation and external auditor signing
outside the local slice.
When a production-like `schema_registry_ops_report.v1` for `staging` or `prod` is attached, passes,
has `readiness_state=production_like_ready`, uses external registry evidence, has signed attestation,
has hash-bound publication evidence, covers P0 source subjects and proves per-subject contract hash,
payload schema hash, schema/artifact id, compatibility, producer schema-id enforcement plus
broker/sink validation, the pack sets `schema_registry_release_gate_passed=true` and removes the
`schema-registry-compatibility` capability blocker. A local preflight ops report never removes this
capability blocker, even when it passes.
When staging/prod `semantic_metric_serving_ops_report.v1` is attached with
`readiness_state=production_like_ready`, `mode=runtime_attested`, all metrics certified, approved
certification evidence, explicit semantic view manifest, passing deployment evidence, usage tracking
evidence and zero failed checks/metrics, the pack sets
`semantic_metric_serving_release_gate_passed=true` and removes the `semantic-metric-serving`
capability blocker. A local semantic serving preflight never removes this capability blocker, even
when it passes.
When staging/prod `source_activation_ops_report.v1` is attached with
`readiness_state=production_like_ready`, `mode=runtime_attested`, a valid activation ledger, every
registered P0 source active and production-ready, valid active pointers, valid runtime-readiness
hash evidence, hash-verifiable readiness/bundle/runtime artifacts and zero
registry-drift/runtime/pointer/evidence-integrity issues, the pack sets
`source_onboarding_release_gate_passed=true` and removes the `source-onboarding` capability blocker.
A staging/prod report with any unactivated or non-active P0 source is `passed=false` at the artifact
source, not merely blocked later by Control Tower. A local source activation preflight never removes
this capability blocker, even when it passes.
When staging/prod `backfill_readiness_report.v1` is attached with `mode=runtime_attested`,
`readiness_state=ready`, zero failed checks and all required backfill evidence references local and
hash-bound, the pack sets `backfill_change_governance_release_gate_passed=true` and removes the
`backfill-change-governance` capability blocker. Metadata-only or local preflight backfill evidence
does not remove this blocker.
CI enforces this through `make source-onboarding-release-gate`; current failures preserve
`build/source-activation-ops/staging.json`,
`build/source-onboarding-review-pack/production-review-pack.json` and
`build/production-review-gates/source-onboarding-release-gate.json` for reviewer inspection.
When `schema_registry_auth_smoke_report.v1` is attached and proves token-based allow/deny
enforcement plus authorization audit evidence, the pack removes
`production_registry_authentication_authorization` while still keeping registry HA storage,
enterprise OIDC/Keycloak, secret rotation and external gateway controls outside the local slice.
When `schema_registry_storage_smoke_report.v1` is attached and proves SQL-backed shared storage,
cross-replica read-after-write and replica restart durable read-back, the pack removes
`production_registry_ha_storage` while still listing managed HA database, multi-AZ, failover
routing and backup/restore/PITR as local-slice limitations.
When staging/prod `catalog_lineage_ops_report.v1` is attached with
`readiness_state=production_like_ready`, `mode=runtime_attested`, zero owner/steward/static/runtime
lineage gaps, valid non-local OpenLineage events, a passing catalog publish manifest and a publish
receipt that binds the catalog bundle hash, publish manifest hash, OpenLineage hash, environment and
target endpoint, the pack sets `catalog_lineage_release_gate_passed=true` and removes the
`catalog-lineage-control-plane` capability blocker. A local preflight ops report never removes this
capability blocker, even when it passes.
If the optional object-store smoke is not attached, it adds `object_store_commit_smoke_not_attached`.
When object-store and Trino Iceberg/MinIO evidence prove SSE-S3 bucket policy enforcement,
unencrypted PUT denial and encrypted Iceberg objects, the pack removes
`production_object_store_encryption_policy` while still listing production cloud KMS/key-rotation
and external attestation gaps as out of scope for the local smoke.
If the optional Iceberg catalog smoke is not attached, it adds `iceberg_catalog_smoke_not_attached`.
If the optional Trino SQL smoke is not attached, it adds `trino_sql_runtime_smoke_not_attached`.
If the optional Trino Iceberg/MinIO smoke is not attached, it adds
`trino_iceberg_minio_smoke_not_attached`.
When `catalog_cross_engine_smoke_report.v1` is attached and proves Trino/PyIceberg shared-catalog
read/append compatibility, the pack removes `cross_engine_commit_compatibility` while still keeping
production catalog HA, managed failover, backup/restore/PITR and production concurrency controls as
local-slice limitations.
When `catalog_runtime_ops_report.v1` is attached from staging/prod and strict-passing, the pack
removes `production_catalog_ha`, `production_catalog_concurrency_locking`,
`managed_catalog_failover`, `multi_az_catalog_deployment` and
`production_catalog_backup_restore_pitr`. The same report does not remove `platform-runtime-iac`,
`catalog-lineage-control-plane`, `semantic-metric-serving`, source onboarding, schema registry,
security or orchestration blockers.
If the optional Trino runtime security smoke is not attached, it adds
`trino_runtime_security_smoke_not_attached`.
When `policy_decision_smoke_report.v1` is attached and proves OPA allow/deny, row-filter, mask,
policy-admin maker-checker and audit evidence, the pack removes `ranger_or_opa_policy_decision_point`
and `policy_admin_maker_checker` while still listing OIDC/Keycloak, HA PDP, signed bundle
distribution, SIEM export and secret rotation as local-slice limitations.
When `oidc_auth_smoke_report.v1` is attached and proves JWKS publication, RS256 signature
validation, issuer/audience/expiry checks, required-role denial, unknown-`kid` denial, missing-token
denial and redacted audit evidence, the pack removes `keycloak_or_oidc_authentication` while still
listing enterprise Keycloak realm deployment, managed IdP HA, group sync, managed JWKS rotation and
production secret rotation as local-slice limitations.
When all three access/privacy artifacts are attached and strict-passing (`trino_runtime_security_smoke_report.v1`,
`policy_decision_smoke_report.v1` and `oidc_auth_smoke_report.v1`), the pack sets
`access_privacy_release_gate_passed=true` and removes the P0 `access-privacy-enforcement` capability
blocker from Control Tower backlog import. It still keeps independent P0 blockers for production
secret rotation, HA identity/PDP operations, signed policy distribution, SIEM export and broader
runtime/IaC evidence.
When `secret_rotation_smoke_report.v1` is attached and proves local encrypted version rotation,
old-version revoke, service-identity authorization, missing-secret denial, Dagster injection by
secret handle/version and redacted audit evidence, the pack removes
`orchestrator_service_identity_and_secret_injection` while still keeping `production_secret_rotation`
as a P0 blocker until managed secret manager/KMS/workload identity/rotation-policy evidence exists.
When staging/prod `secret_rotation_ops_report.v1` is attached and strict-passing, the pack sets
`secret_rotation_ops_release_gate_passed=true` and removes production secret/KMS blockers such as
`production_secret_rotation`, `production_cloud_kms_key_rotation`, `cloud_kms_or_hsm_key_custody`,
`managed_secret_manager_ha`, `workload_identity_federation_to_cloud`,
`automatic_rotation_scheduler`, `cross_region_secret_replication` and `siem_audit_export`. Local
or missing evidence never closes those gaps.
When staging/prod `runtime_readiness_report.v1` is attached, or built inside the pack from
`runtime_iac_plan_evidence.v1`, `runtime_iac_apply_evidence.v1`,
`runtime_iac_drift_report.v1`, `runtime_backup_evidence.v1`,
`runtime_service_health_evidence.v1` and production `runtime_dr_evidence.v1`, the pack sets
`runtime_iac_release_gate_passed=true` and removes the `platform-runtime-iac` capability blocker.
Local readiness, synthetic fixture evidence, missing DR, partial service coverage, drift, failed
backup/health checks or destructive production plans keep the blocker in place. This still does not
remove independent blockers for production catalog HA/concurrency, managed secret rotation, broker
secret rotation, distributed Dagster execution or source onboarding maturity.
If the optional Dagster smoke is not attached, it adds `dagster_orchestration_smoke_not_attached`.
When `dagster_day2_smoke_report.v1` is attached and strict-passing, the pack sets
`dagster_day2_release_gate_passed=true` and removes the `dagster_daemon_or_schedule_tick_history`,
`production_retry_backoff_runtime_policy` and `production_backfill_materialization_history` gaps from
the Dagster orchestration boundary. It still keeps `distributed_executor_or_kubernetes_run_launcher`
and does not claim production Dagster daemon HA, managed run storage, production backfill scheduling
or orchestrator metrics export. When a staging/prod `orchestration_runtime_ops_report.v1` is
attached and strict-passing, the pack sets `orchestration_runtime_release_gate_passed=true` and
removes the production orchestration runtime gaps for distributed/Kubernetes execution, daemon and
scheduler HA, managed run storage, production retry/backfill/tick history, service identity,
secret injection and metrics export. It does not remove `platform-runtime-iac`, catalog, schema,
semantic serving, source-onboarding or security gates owned by their separate evidence reports.
If the broker ACL smoke is attached but does not prove both allowed produce and denied broker
authorization failure, it adds `broker_acl_smoke_failed`; when the passing report is attached,
`broker_acl_enforcement` is removed from the event-backbone gap backlog.
If the portfolio release smoke is not attached, it also adds `portfolio_release_smoke_not_attached`.
When the portfolio smoke is attached, the pack also carries source activation operations evidence
for the local P0 sources so the partner can trace source readiness from change request to activation
ledger, active pointer and Control Tower decision.

## Non-Negotiables

- BI and ML must not read product OLTP databases directly.
- Every dataset has product ownership, domain ownership, a data steward, SLA, contract version,
  data residency, retention policy and PII classification.
- Raw Bronze data is append-only unless a governed erasure workflow applies.
- Transformations are code-reviewed and deployed through CI/CD.
- Failed quality checks block downstream Gold publication.
- Staging/prod Silver and Gold release gates require `lakehouse_snapshot_evidence.v1` with matching
  pipeline manifest hash, Iceberg snapshot metadata, schema/partition evidence and upstream Bronze
  offset ledger binding.
- Staging/prod Silver and Gold publication requires `silver_gold_publication_ops_report.v1` with
  passing release evidence, approved promotion, activated manifest, active pointer consistency,
  rollback target and production change ticket where applicable.
- Staging/prod backfills require `backfill_readiness_report.v1` before replay, promotion or
  activation of rebuilt outputs.
- Production-impacting data platform changes require registered change-control evidence with
  maker-checker approval, risk level, target environment, rollback plan and impact assessment.
- Cross-tenant and cross-product data access must be row-level isolated and audited.
