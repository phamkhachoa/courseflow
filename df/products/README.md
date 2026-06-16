# Product Onboarding

`products/` is the onboarding boundary for enterprise products that publish data into the platform.
Each product keeps its source-system map, domain mapping, use cases and product-specific exceptions
here. Shared engines, controls and runtime patterns stay under `platform/`.

## Required Product Metadata

Every product folder must define:

- Product code, owner, business sponsor and technical owner.
- Source domains, source services, databases and SaaS feeds.
- Publication modes: outbox, CDC, event collector or batch connector.
- Default governance controls: PII stance, tenant isolation, retention policy, access personas,
  consumer contract, release evidence profile, catalog registration and lineage requirement.
- Initial Bronze, Silver and Gold data products.
- BI, ML, reverse ETL and compliance consumers.

Source domains inside onboarding describe the product's operational boundary. Contract domains are
enterprise data domains and must come from `domains/registry.yaml`.

## Current Products

| Product | Status | Purpose |
|---|---|---|
| `lms-courseflow` | Pilot | First LMS product proving the enterprise ingestion, Medallion, contract, quality and ML handoff pattern. |
| `enterprise-commerce` | Pilot | First non-LMS finance product proving benefit settlement and reconciliation orchestration. |
| `billing-platform` | Pilot | First finance source-of-truth product proving billing transaction and certified revenue daily orchestration. |
| `identity-platform` | Pilot | First compliance/security product proving subject, entitlement and access-risk governance. |
| `crm-sales` | Pilot | First customer-domain product proving Customer 360 identity link and account-health profile orchestration. |
| `support-platform` | Pilot | First customer experience product proving support case state, SLA breach and service journey intelligence. |

Create a planned onboarding pack for a future product:

```bash
enterprise-df product-scaffold \
  --root df \
  --product-code crm-sales \
  --name "CRM Sales" \
  --domain customer \
  --business-sponsor customer-growth-lead \
  --product-owner crm-sales-po \
  --technical-owner crm-sales-sa
```

The scaffold uses `firstSlice.contractStatus=planned`, so a product team can register ownership,
privacy/access defaults and expected first-slice names before topic/data-product contracts exist.
