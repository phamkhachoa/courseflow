# SA Review: Group-Wide Enterprise Data Platform Scope

Date: 2026-06-16
Reviewer: Senior Enterprise Data Platform Architect

## Verdict

`df/` must be treated as a group-wide enterprise data platform. CourseFlow LMS is a product onboarded
onto the platform, not the platform identity. The current implementation is directionally correct
after adding `products/`, `catalog/`, `governance/` and `templates/` as first-class boundaries.

## Required Scope Guardrails

| Guardrail | Decision |
|---|---|
| Product boundary | Every product must live under `products/<product-code>/` with ownership and source-system metadata. |
| Platform boundary | `platform/` contains reusable capabilities only: ingestion, lakehouse, processing, orchestration, quality, governance, security, serving, observability and developer experience. |
| Domain boundary | `domains/` owns enterprise Data Mesh semantics that may span many products. |
| Contract boundary | `contracts/` owns versioned event, topic and data product contracts enforced by CI and schema registry workflows. |
| Catalog boundary | `catalog/` defines metadata-as-code for discovery, glossary, ownership and lineage. |
| Governance boundary | `governance/` defines enterprise policies, council decisions, stewardship and exception handling. |
| Templates boundary | `templates/` provides paved-road onboarding assets for the next product. |

## CourseFlow LMS Placement

CourseFlow-specific terms are allowed in:

- `products/lms-courseflow/**`
- CourseFlow-owned contracts under `contracts/topics/**`, `contracts/events/**` and
  `contracts/data-products/**`
- CourseFlow pilot domain notes under `domains/recommendation/**`
- Local sample data and tests for the first implementation slice

CourseFlow-specific terms should not become hard-coded assumptions in:

- `platform/**`
- contract validator rules
- generic templates
- catalog/governance policy language
- serving and orchestration platform decisions

## Enterprise Metadata Required

Every topic and data product contract must declare:

- Product code.
- Domain and domain owner.
- Product owner, technical owner and data steward where applicable.
- PII classification, tenant isolation, data residency and retention.
- Access personas and consumer contract.
- Lineage requirement and publication gate.
- Deprecation policy for data products.

## SA Decision

Keep CourseFlow LMS as the pilot, but make every new file answer this question: "Can the next
enterprise product reuse this without inheriting LMS assumptions?" If not, place the content under
`products/lms-courseflow/` or make the abstraction explicit.
