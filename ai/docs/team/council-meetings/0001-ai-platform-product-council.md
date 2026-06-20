# AI Platform Product Council 0001

Date: 2026-06-16

## Attendees

| Role | Focus |
|---|---|
| PO/BA Agent | Product portfolio, KPI, enterprise backlog |
| SA AI Platform Agent | Platform boundaries, multi-domain architecture, readiness gates |
| SA AI Engineer Agent | Implementation path, registry validation, dependency/test strategy |
| Governance Reviewer | Privacy, tenant isolation, safety, HITL, audit |

## Decision

`ai/` is a standalone Enterprise AI Platform product. LMS remains the first onboarded product and AI Mentor remains the first umbrella use case, but the platform must serve multiple domains: support, billing/finance, identity/risk, commerce and workforce.

## Key Proposals

1. Add platform product charter and product registry.
2. Expand use-case registry beyond LMS.
3. Treat capability and use-case registries as validated platform inputs, not informal notes.
4. Add platform validation tooling under `ai/platform`.
5. Keep recommendation service as first runtime service, not the platform itself.

## Actions

| Action | Owner | Status |
|---|---|---|
| Create AI Platform product charter | PO/BA Agent | done |
| Add product registry for multi-domain onboarding | SA AI Platform Agent | done |
| Expand use-case portfolio beyond LMS | PO/BA Agent | done |
| Implement registry validation primitive | SA AI Engineer Agent | in progress |
| Keep CI/build path aligned to `ai/services` | SA AI Engineer Agent | done |

## Exit Criteria For Next Council

- `ai/products/registry.yaml` validates.
- `ai/use-cases/registry.yaml` includes at least five non-LMS use cases.
- `ai/platform` has executable registry validation tests.
- README positions AI Platform as a product, not merely an LMS support folder.

