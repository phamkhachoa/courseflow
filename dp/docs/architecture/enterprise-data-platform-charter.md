# Enterprise Data Platform Charter

Status: accepted for implementation

Date: 2026-06-16

## Decision

`dp/` is the group-wide enterprise data platform for the corporation. It is not an LMS data mart,
not a CourseFlow extension and not a single-product warehouse. CourseFlow LMS is only the first
onboarded product used to prove the platform operating model.

The foundation must support many current and future enterprise products, including commerce,
payment, billing, CRM, support, HRIS, identity, risk, compliance, AI assistants, internal portals and
business applications that have not been created yet.

## Platform Promise

The platform provides reusable capabilities for:

- Product source onboarding through contracts, outbox, CDC, event collectors and governed batch.
- Bronze, Silver and Gold lakehouse products with reproducible snapshots.
- Enterprise data domains with owners, stewards, quality SLOs and consumer contracts.
- Financial reconciliation, Customer 360, workforce analytics, product analytics, risk and
  compliance reporting.
- ML/AI feature datasets, model-training snapshots and reverse ETL handoff.
- Evidence-backed release, backfill, rollback, access, retention and lineage governance.

## Boundary Rules

- Product-specific facts live under `products/<product-code>/`, product contracts or product-owned
  sample data.
- Shared standards under `platform/`, `catalog/`, `governance/`, `templates/` and
  `src/enterprise_dp/` must use enterprise-neutral vocabulary unless they are explicitly marked as a
  pilot compatibility appendix.
- Enterprise domains under `domains/` define reusable business semantics that may span many
  products.
- A new use case should add a product onboarding pack, source registry entry, contracts, data
  products and pipeline runner. It should not create a new platform stack.
- BI and ML workloads consume approved Gold, semantic or feature layers, never product OLTP
  databases directly.

## Required Product Onboarding Shape

Every product entering the foundation must register:

- Product code, owner, sponsor, technical owner and data steward.
- Source systems, publication modes, source services and source identity.
- Enterprise domains, initial use cases and first Bronze/Silver/Gold data products.
- Privacy, tenant isolation, residency, retention and access defaults.
- Release evidence profile, catalog registration and lineage requirement.
- First consumer set for BI, ML, reverse ETL, operations, finance or compliance.

## Architecture Implication

The shared platform should be boring and repeatable. Product teams bring business facts; the
enterprise data platform brings contracts, landing, lakehouse storage, transformations, quality,
catalog, security, release governance and operational evidence.

Any change that makes `dp/` hard to reuse for the next non-LMS product must be treated as an
architecture regression.
