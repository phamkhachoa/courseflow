# Enterprise Reporting Data Domain

This domain owns the KPI catalog, semantic metrics, executive scorecards and cross-domain reporting
contracts for the enterprise data platform.

## Business Capability

Enterprise Reporting creates consistent, governed metrics for leadership, operating reviews,
financial reporting packs and cross-functional scorecards. It depends on source domains for
business-ready facts and owns the semantic definitions that make KPIs comparable.

## First Data Products

| Data product | Purpose | First source or contribution |
|---|---|---|
| `gold.enterprise_kpi_daily` | Daily cross-domain KPI facts with owner, definition and certification status. | Finance, customer, support, identity risk, recommendation and Control Tower semantic metrics. |
| `gold.executive_scorecard_daily` | Executive-ready scorecard facts by product, region, organization and period. | Non-PII leadership scorecard rows sourced from certified semantic snapshots. |
| `semantic.enterprise_metrics` | Governed semantic metric views for BI and self-service. | Shared metric definitions across Billing, Commerce, CRM, Support, Identity, LMS and platform control-plane data. |

## First Consumers

- Executive leadership for operating rhythm and strategic decisions.
- Strategy and operations for cross-product planning and performance management.
- Finance for certified financial and operating metric packs.
- Product leadership for portfolio health and product comparison.

## Product Contributions

CourseFlow LMS contributes recommendation and learner engagement signals, but it is only one source
product. Billing, Commerce, CRM Sales, Support Platform, Identity Platform and the Enterprise Data
Foundation control plane contribute the first production-style executive KPI slice.

## Future Product Onboarding

- Finance domain for revenue, margin, forecast and reconciliation KPIs.
- Customer success systems for retention, health and support KPIs.
- People operations for workforce readiness and training compliance KPIs.
- Sales operations for pipeline, conversion and account lifecycle KPIs.

## Domain-Specific Rules

- Every certified metric must have an owner, definition, grain, filter rules and freshness SLO.
- Executive scorecards must identify whether a metric is certified, provisional or exploratory.
- Semantic views must reference approved Gold data products or approved domain aggregates.
- Metric changes require version notes and backward-compatibility assessment for recurring reports.
