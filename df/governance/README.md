# Enterprise Data Governance

`governance/` defines the operating model for the group-wide data platform. Platform engineering owns
the paved road; product and domain owners remain accountable for business meaning, quality and access
approval.

## Governance Model

| Role | Accountability |
|---|---|
| Enterprise Data Council | Approves platform standards, cross-domain definitions and risk exceptions. |
| Product Owner | Owns source-system onboarding, business priority and consumer commitments. |
| Domain Owner | Owns domain semantics, definitions and Gold publication readiness. |
| Data Steward | Owns catalog quality, PII tagging, retention, residency and access review evidence. |
| Data Platform Team | Owns shared ingestion, lakehouse, orchestration, quality, security and serving capabilities. |

## Enterprise Policies

- No BI, ML or ad-hoc analysis reads directly from product OLTP databases.
- Cross-product datasets must use approved common dimensions for tenant, product, person, org and time.
- Gold data products require passing quality gates, catalog lineage and access policy before publish.
- Sensitive data requires masking/tokenization before self-service access.
- Product teams must publish deprecation windows for breaking contract changes.
- Shared platform areas must not silently depend on the first product pilot. `scope-guardrails.yaml`
  records reviewed exceptions and CI rejects unreviewed product-specific identity in protected paths.

## Access Grant Evidence

`access-grants.yaml` records approved, time-bound data access grants for governed Silver and Gold
serving products. Each grant ties a consumer persona to a data product, access policy, consumer
contract, business purpose, owner/steward approval, expiry date and review cadence.

Release evidence must prove both sides:

- The data product contract passes reusable policy checks.
- Each non-platform consumer persona has an active grant with required approval evidence and runtime
  allow/deny audit decisions.

## Enterprise Change Control

`change-requests.yaml` is the metadata-as-code control plane for platform-impacting changes. It is
group-wide by design and applies to source onboarding, schema changes, data product publish, access
grant changes, catalog publication, semantic-layer changes, retention exceptions and use-case
onboarding.

Each request records requester, target environment, product/domain/use-case references, risk level,
change ticket, maker-checker approvals, evidence URIs, rollback control and impact assessment. The
CLI writes an auditable evidence report:

```bash
enterprise-df change-control-check \
  --root df \
  --request-id publish_finance_benefit_reconciliation_prod \
  --environment prod \
  --output /tmp/change-control.json
```

Production-like requests must have separate approvers, data steward approval, platform owner approval,
required evidence for the request type, rollback evidence and impact assessment. Sensitive production
data products also require security or privacy approval.
