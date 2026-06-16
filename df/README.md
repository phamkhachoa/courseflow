# Enterprise Data Platform

`df/` is the implementation home for the group-wide enterprise data platform. It is intentionally a
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

Build a production-ready, enterprise-grade data foundation for the group:

- Keep OLTP service databases protected from BI, ad-hoc analytics and ML training workloads.
- Onboard product source systems through versioned contracts, CDC, outbox streams or governed batch
  connectors.
- Publish governed Bronze, Silver and Gold data products with ownership, contracts, lineage and SLOs.
- Support BI, finance/reconciliation, Customer 360, workforce analytics, product analytics, risk,
  compliance, ML feature stores and reverse ETL from trusted analytical layers.
- Make every pipeline reproducible, observable, idempotent and auditable.

The scope decision is captured in
[`docs/architecture/enterprise-foundation-charter.md`](docs/architecture/enterprise-foundation-charter.md):
`df/` is the corporation's reusable data foundation. LMS examples are pilot evidence, not platform
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

## Folder Layout

| Path | Purpose |
|---|---|
| `contracts/` | Event envelope, topic contracts, data product contract templates and compatibility rules. |
| `products/` | Product onboarding boundary. CourseFlow LMS, Enterprise Commerce, Billing Platform, Identity Platform, CRM Sales, Support Platform and Enterprise Data Foundation are the first product examples. |
| `domains/` | Enterprise Data Mesh domain ownership and cross-product business semantics. |
| `use-cases/` | Group-wide PO/BA use-case and data-product portfolio registry. |
| `platform/` | Shared ingestion, lakehouse, processing, orchestration, quality, governance, security, serving and ops capabilities. |
| `platform/capabilities/` | Enterprise capability maturity registry, reference-model mapping and production readiness report inputs. |
| `platform/control-tower/` | Data Product Control Tower operating model, P0 blocker taxonomy and report contract. |
| `catalog/` | Metadata-as-code guidance for glossary, ownership, discovery and lineage registration. |
| `governance/` | Enterprise governance model, domain council rules and policy ownership. |
| `templates/` | Scaffolds for new products, domains and data products. |
| `docs/` | Architecture, ADRs, structure reviews, team operating model, roadmap and BA/PO use cases. |
| `src/enterprise_df/` | Developer tooling for contract and structure validation. |
| `tests/` | Automated checks for platform tooling, contracts and local pipeline skeletons. |

## Implemented Now

- Contract validator CLI: `enterprise_df.cli`.
- Product onboarding scaffold CLI: `enterprise-df product-scaffold`.
- Local Bronze ingestion preflight CLI: `enterprise-df ingest-bronze`.
- Local catalog/lineage export CLI: `enterprise-df catalog-export`.
- OpenLineage-style runtime event export CLI: `enterprise-df openlineage-export`.
- Observability and cost-attribution metrics export CLI: `enterprise-df observability-export`.
- Catalog publish manifest CLI: `enterprise-df catalog-publish-manifest` for DataHub/OpenMetadata
  publish evidence.
- Ed25519 external evidence attestation verification with metadata-as-code trust key registry.
- Local schema registry compatibility report CLI: `enterprise-df schema-registry-check`.
- Local access-policy evidence CLI: `enterprise-df access-policy-check`.
- Enterprise change-control evidence CLI: `enterprise-df change-control-check` over
  `governance/change-requests.yaml` for source onboarding, schema changes, access grants, catalog
  publish and Gold data product release approvals.
- Local pipeline runner registry CLI: `enterprise-df pipeline-list`, `enterprise-df pipeline-describe`
  and `enterprise-df run-pipeline`.
- Generic use-case orchestration CLI: `enterprise-df run-use-case`, driven by
  `use-cases/registry.yaml` implementation metadata.
- Release promotion and activation manifest CLIs: `enterprise-df release-promote` and
  `enterprise-df release-activate`; activation writes the active pointer state for the approved
  data-product snapshot.
- Local P0 recommendation slice orchestration CLI: `enterprise-df run-recommendation-slice`
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
  Platform, CRM Sales, Support Platform, HRIS Workforce and Enterprise Data Foundation.
- Product-level governance onboarding controls for privacy, retention, access, catalog lineage and
  release evidence defaults.
- Product-agnostic source bridge preflight CLI: `enterprise-df source-bridge-normalize`; it converts
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
  staging/prod OpenTofu skeletons, Dremio/TiDB phase gates and `enterprise-df
  runtime-readiness-check` evidence reports. Production-like reports can consume machine-readable
  plan/apply/drift/backup/DR/health evidence produced or normalized by `enterprise-df
  runtime-evidence-pack`; local can pass developer preflight, while staging/prod remain not-ready
  until valid live evidence is attached.
- Source registry and validator for product source onboarding, canonical topic bridges, schema
  subjects, Bronze targets, privacy handling and production evidence requirements.
- Source-to-Bronze readiness report CLI: `enterprise-df source-readiness-check`; it gates source
  activation with bridge manifest, ingestion, replay, schema, change-control, catalog and OpenLineage
  evidence.
- Source readiness bundle CLI: `enterprise-df source-readiness-bundle`; it runs the repeatable
  source-to-Bronze evidence path end to end for direct-canonical or bridge-required sources so
  source promotion decisions can be reviewed from one artifact pack.
- Source activation ledger under `governance/source-activations.yaml`; portfolio readiness can use
  it as an evidence-backed overlay so static registry status stays honest while approved activation
  records provide `effective_status=production_ready` for the matching environment.
- Source activation CLI: `enterprise-df source-activate`; it creates `source_activation_manifest.v1`
  from a passed source readiness bundle, computes hashes from the actual bundle/readiness/registry
  files, enforces maker-checker and change-request alignment, appends the activation ledger only when
  gates pass and writes a per-source active pointer for rollback/review.
- Source revocation CLI: `enterprise-df source-revoke`; it appends a `revoked` activation event,
  requires an approved `source_activation_revoke` change request and overwrites the per-source active
  pointer with a tombstone so portfolio readiness blocks the source again without mutating history.
- Source activation operations report CLI: `enterprise-df source-activation-ops-report`; it audits
  activation ledger health, active-pointer consistency, expiry, registry hash drift and revocation
  state across registered enterprise sources.
- Source offset ledger CLI: `enterprise-df offset-ledger-record`; it records partition watermarks,
  replay idempotency, row-hash bindings and Iceberg snapshot evidence for Bronze commits.
- Lakehouse snapshot evidence CLI: `enterprise-df snapshot-evidence-record`; it binds Silver/Gold
  pipeline outputs to Iceberg snapshot metadata, contract hashes, schema hashes, partition spec
  hashes, upstream offset ledger evidence and release/use-case/runner identity.
- Backfill/replay readiness CLI: `enterprise-df backfill-readiness-check`; it gates bounded
  production-like backfills with approved scope, dry-run, data-diff, source offset ledger,
  lakehouse snapshot evidence, change-control, rollback, impact and communication evidence.
- Pipeline registry manifest and validator for runnable pipeline metadata, use-case bindings,
  input/output data products, evidence capabilities and implementation parity.
- Semantic metric registry and validator for governed finance, compliance/access-risk,
  recommendation and executive KPI definitions over approved Gold data products.
- Semantic view manifest export CLI: `enterprise-df semantic-views-export` for Trino/Dremio view SQL
  generated from the metric registry.
- Enterprise capability maturity registry and report CLI: `enterprise-df capability-maturity-report`;
  it shows which P0/P1 platform capabilities are still below production target maturity.
- Enterprise portfolio readiness report CLI: `enterprise-df portfolio-readiness-report`; it joins
  product onboarding, use-case demand, first-slice contracts and source-readiness gaps into a PO/BA
  decision board for what enterprise product/use case should be implemented next. Pass
  `--source-activation-ledger governance/source-activations.yaml` when PO/SA want the board to honor
  approved source readiness activations.
- Data Product Control Tower report CLI: `enterprise-df control-tower-report`; it aggregates
  catalog, quality, lineage, access, release evidence and capability maturity into a P0 production
  signoff decision report.
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
cd df
make check
```

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
- Staging/prod backfills require `backfill_readiness_report.v1` before replay, promotion or
  activation of rebuilt outputs.
- Production-impacting data platform changes require registered change-control evidence with
  maker-checker approval, risk level, target environment, rollback plan and impact assessment.
- Cross-tenant and cross-product data access must be row-level isolated and audited.
