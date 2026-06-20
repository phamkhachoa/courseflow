# Developer Experience

Developer experience owns the paved road for product teams and domain teams that onboard data into
the enterprise platform.

## Scope

- Product onboarding templates and checklists.
- Local validation commands and CI integration.
- Contract scaffolding and compatibility checks.
- Example pipeline skeletons and sample data conventions.
- Documentation standards for source mapping, lineage and runbooks.

## Rules

- New products should start from `templates/product-onboarding.template.yaml`.
- Local checks must be runnable with `cd dp && make check`.
- Examples must avoid product-specific assumptions unless they live under `products/<product-code>/`
  or are clearly marked as a pilot slice.
