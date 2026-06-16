# Data Product Control Tower

`platform/control-tower/` defines the P0 operating view for enterprise data product health. It is
owned by the data platform team and consumed by domain owners, governance, security, enterprise
reporting and approved BI/ML consumers.

## Purpose

The Control Tower is an evidence aggregator and decision report. It does not replace lower-level
validators. It reads contracts, catalog metadata, lineage, quality profiles, release evidence, access
governance and capability maturity reports, then surfaces which data products can or cannot move
toward production signoff.

The local materialization runner `control_tower.materialize_gold.from_report.v1` turns that decision
report into four dashboard-ready Gold JSONL outputs:

- `gold.data_product_inventory`
- `gold.contract_compliance_daily`
- `gold.quality_sla_daily`
- `gold.lineage_coverage_daily`

## Required Views

| View | Decision |
|---|---|
| Executive health overview | Which domains/products are blocked and why. |
| Data product inventory | Owner, steward, lifecycle, classification, SLO and readiness per data product. |
| Contract compliance | Contract validity, lifecycle state, schema/quality/access/retention coverage. |
| Quality and SLA board | Freshness, release evidence, runtime lineage and blocking quality state. |
| Lineage coverage | Static catalog lineage and runtime run evidence per data product. |
| Access/privacy board | Policy, consumer contract and grant evidence coverage. |
| Capability maturity | P0 platform capability current level vs target level. |

## P0 Blocking Rules

- Data product contract validation fails.
- Gold data product is not `ACTIVE`.
- Gold data product lacks quality profile coverage.
- Required catalog or runtime lineage is missing.
- Silver/Gold serving data product fails access policy or consumer contract checks.
- Gold data product has no passing release evidence.
- P0 platform capabilities are still below target maturity.

`enterprise-df control-tower-report` intentionally exits non-zero while these blockers exist. This is
the expected production signoff behavior.

## Local Flow

```bash
enterprise-df control-tower-report \
  --root . \
  --output build/control-tower/report.json

enterprise-df run-use-case \
  --root . \
  --use-case data-product-control-tower \
  --input build/control-tower/report.json \
  --output-dir build/control-tower/run \
  --release-id local-control-tower \
  --environment local
```
