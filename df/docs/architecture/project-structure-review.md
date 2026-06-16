# SA Review: Data Platform Project Structure

Date: 2026-06-16
Reviewer: Senior Data Platform Architect

## Verdict

The decision to create a top-level `df/` workspace is correct. A production data platform should not
be buried inside `backend/analytics-service`, because it owns cross-product analytical products,
lakehouse pipelines, governance, contracts, catalog metadata and ML feature handoff for the group.

The structure must not identify the whole platform with CourseFlow LMS. CourseFlow is the first
onboarded product, while `platform/`, `contracts/`, `catalog/`, `governance/` and `templates/` must
remain reusable for the next enterprise product.

## Reviewed Criteria

| Criterion | Assessment | Decision |
|---|---|---|
| Top-level boundary | Good | Keep `df/` beside `ai/` and `backend/`. |
| Product onboarding | Required | Add `products/<product-code>/`; start with `products/lms-courseflow/`. |
| Domain ownership | Good with caveat | Use `domains/` for enterprise Data Mesh semantics, not product folders. |
| Shared platform capabilities | Good | Keep runtime capabilities under `platform/`. |
| Contract enforcement | Good start | Keep central `contracts/` and validator; require enterprise metadata. |
| Catalog metadata | Missing before | Add `catalog/` as metadata-as-code boundary. |
| Governance ownership | Missing before | Add `governance/` for council, stewardship and policy model. |
| Onboarding repeatability | Missing before | Add `templates/` for new products and data products. |
| Environment separation | Good | Keep `platform/environments/{local,staging,prod}`. |
| Operability | Good | Keep `platform/observability` and release gates. |

## Approved Structure

```text
df/
  contracts/              # versioned event/topic/data-product contracts and policies
  products/               # product onboarding boundary
    lms-courseflow/
      domains/
      use-cases/
      onboarding.yaml
  domains/                # enterprise Data Mesh domains and shared business semantics
  platform/               # shared platform capabilities
    ingestion/
    lakehouse/
    processing/
    orchestration/
    quality/
    governance/
    serving/
    observability/
    security/
    developer-experience/
    environments/
      local/
      staging/
      prod/
  catalog/                # metadata-as-code for discovery, glossary and lineage
  governance/             # enterprise governance, stewardship and exception model
  templates/              # scaffolds for future products/domains/data products
  src/enterprise_df/      # validation and platform developer tooling
  tests/                  # tests for platform tooling, contracts and local pipelines
  docs/                   # architecture, ADRs and reviews
```

## SA Decision

Use this structure before implementing more pipelines. Future work should onboard new products under
`products/<product-code>/`, define reusable enterprise semantics under `domains/`, and register
enforceable schemas/contracts under `contracts/`. Platform-wide runtime concerns must go under
`platform/`, not inside individual products.
