# ADR 0003: Group-Wide Enterprise Data Platform Scope

Status: accepted

Date: 2026-06-16

## Context

The initial `dp/` work started from CourseFlow LMS because it is the first product with concrete
source systems, recommendation ML needs, incentive/finance data and operational analytics pressure.
The group now needs `dp/` to support many enterprise products, not only LMS.

If the platform identity remains CourseFlow-specific, future products will either copy the folder
structure or overload LMS concepts such as learner, course, enrollment and gradebook. That would
break the enterprise platform goal.

## Decision

`dp/` is the group-wide enterprise data platform. CourseFlow LMS is registered as the first product
under `products/lms-courseflow/`.

The platform will use these boundaries:

- `platform/`: shared reusable capabilities.
- `products/`: product onboarding, product source maps and product-specific use cases.
- `domains/`: enterprise Data Mesh domains and cross-product business semantics.
- `contracts/`: versioned topic and data product APIs.
- `catalog/`: metadata-as-code for discovery, glossary, ownership and lineage.
- `governance/`: enterprise policies, stewardship and exception model.
- `templates/`: paved-road scaffolds for the next product.

## Consequences

- Tooling is renamed from `courseflow_df` to `enterprise_dp`.
- Contract metadata must include product, domain owner, data steward, data residency, access personas
  and consumer contract details.
- CourseFlow LMS contracts remain valid as the first product slice, but new products must not copy LMS
  assumptions into `platform/`.
- Dremio and TiDB remain phase-gated technology choices. They are part of the stack, but not P0
  dependencies for the enterprise platform foundation.

## Follow-Up

- Add onboarding templates for the next enterprise product.
- Keep CI scope guardrails active so platform files cannot depend on product-specific identifiers
  without a reviewed allowlist entry.
- Add canonical enterprise dimensions for tenant, product, organization, person and time.
