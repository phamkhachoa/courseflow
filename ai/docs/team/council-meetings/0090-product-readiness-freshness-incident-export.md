# Council 0090: Product Readiness Freshness Incident Export

Date: 2026-06-17

## Participants

| Role | Decision focus |
| --- | --- |
| PO/BA | Convert product-readiness freshness failures into visible stakeholder-ready work |
| SA AI Platform | Keep incident export snapshot-backed and independent from runtime probe execution |
| SA AI Engineer | Classify stale snapshots, route failures, serving errors and audit gaps into P0/P1 incidents |
| Governance Reviewer | Preserve tenant safety by hashing product references and omitting raw runtime payloads |
| Admin/Ops | Route open freshness incidents into owner views and dashboard handoffs |

## Decision

Add `product-readiness-freshness-incident-export-v1` as a tenant-safe governance report.
The export reads the checked-in Product Readiness Freshness snapshot and emits no baseline
incident while the snapshot is current. It opens incidents when the freshness report is stale,
the runtime readiness route is unreachable, the static readiness snapshot is stale, or runtime
request/audit/error counters indicate an audit coverage gap.

## Runtime Evidence

| Surface | Result |
| --- | --- |
| Incident export | `platform/governance/reports/product-readiness-freshness-incident-export-v1.yaml` is current with 0 open incidents |
| Admin/Ops dashboard | Adds Product Incidents counter and Product Readiness Freshness Incident Export panel |
| Owner views | Open P0/P1 product freshness incidents route to `admin-ops` |
| Product readiness | Tenant-safe incident gate now includes serving-access, Governance Evaluation and product freshness exports |
| Freshness manifest | Admin/Ops dashboard source tracking includes the product freshness incident export |

## Outcome

Product readiness freshness is now operationally actionable. A stale report, route outage or
runtime audit gap becomes an owner-routed incident instead of remaining only a failed check in
the product readiness freshness report.

## Next Step

Add a product-readiness freshness incident response drill so Admin/Ops can prove the recovery
path for report refresh, route triage and audit coverage restoration. This is implemented in
Council 0091.
