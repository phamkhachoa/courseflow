# ADR 0001: Data Platform Project Structure

Status: Accepted
Date: 2026-06-16

## Context

The group needs an enterprise data platform based on the reference blueprint in
`ai/enterprise-data-platform-blueprint.html`. The platform must support many products and use cases:
BI, Customer 360, workforce analytics, financial reconciliation, ML training, feature store,
governance and compliance. CourseFlow LMS is the first onboarded product, not the platform boundary.

Placing this work under `backend/analytics-service` would couple analytical workloads to an
operational read-model service. A flat `df/` folder would also become hard to scale as domains and
pipelines grow.

## Decision

Create `df/` as a top-level workspace and organize it into:

- `contracts/` for centrally enforced versioned contracts.
- `products/` for product onboarding metadata and product-specific source/use-case mapping.
- `domains/` for Data Mesh ownership and domain-specific semantics.
- `platform/` for shared platform capabilities, processing standards, developer experience and
  environment overlays.
- `catalog/` for metadata-as-code around discovery, glossary, ownership and lineage.
- `governance/` for enterprise policy, stewardship and exception handling.
- `templates/` for reusable scaffolds for the next product/domain/data product.
- `src/enterprise_df/` for platform developer tooling.
- `tests/` for validation tests.

## Consequences

Positive:

- Clear boundary from backend OLTP services.
- Clear boundary between enterprise platform capabilities and product-specific onboarding.
- Domain teams can own data products without owning shared infrastructure.
- Platform team can enforce contracts, quality and governance centrally.
- The structure scales to many products, data products, analytics and ML use cases.

Tradeoffs:

- Some metadata appears in both domain documentation and central contracts.
- CI must enforce that domain docs and contracts stay aligned.
- Early implementation has more folders than a small prototype, but the shape avoids painful moves
  later.
