# Enterprise Data Use-Case Roadmap

Status: draft for PO/BA prioritization

Date: 2026-06-16

## PO/BA Decision

The data platform must be planned around enterprise operating outcomes, not around a single LMS
product. CourseFlow remains a pilot contributor, while the roadmap expands to identity, CRM,
billing, support, HRIS, commerce, risk, compliance and future products.

## P0 Use Cases

| Order | Use case | Business outcome | First data products |
|---:|---|---|---|
| 1 | Identity, Entitlement and Access Governance | Trusted subject, tenant, entitlement and access audit foundation for every downstream product. | `silver.identity_subject`, `silver.entitlement_assignment`, `silver.audit_access_events`, `gold.access_risk_daily` |
| 2 | Data Product Control Tower | One place to see contract compliance, quality, lineage, ownership, release state and SLA health. | `gold.data_product_inventory`, `gold.contract_compliance_daily`, `gold.quality_sla_daily`, `gold.lineage_coverage_daily` |
| 3 | Enterprise Customer 360 and Account Health | Retention, expansion and service health across CRM, billing, support, product usage and LMS signals. | `silver.customer_identity_link`, `gold.customer_360_profile`, `gold.account_health_daily`, `gold.customer_lifecycle_stage` |
| 4 | Enterprise Revenue and Margin Intelligence | Certified revenue, discount, refund, COGS, gross margin and customer/product profitability. | `silver.billing_transaction`, `silver.payment_event`, `silver.contract_subscription`, `gold.revenue_daily`, `gold.margin_daily` |
| 5 | Executive KPI and Operating Scorecard | Governed semantic metrics for group leadership with lineage and drill-through to certified Gold. | `semantic.enterprise_metrics`, `gold.enterprise_kpi_daily`, `gold.executive_scorecard_daily` |

## P1 Use Cases

| Use case | Business outcome | First data products |
|---|---|---|
| Sales Pipeline, Contract and Renewal Intelligence | Forecast, win/loss, renewal, expansion and contract leakage. | `silver.sales_opportunity`, `silver.contract_terms`, `gold.pipeline_forecast_daily`, `gold.renewal_risk_daily` |
| Risk, Fraud and Control Exception Management | Unified risk and exception queue across payment, commerce, identity, support, finance and learning systems. | `gold.risk_signal_daily`, `gold.control_exception_daily`, `gold.case_queue`, `gold.fraud_pattern_daily` |
| Workforce Skills, Capacity and Productivity Intelligence | Skills, staffing capacity, training compliance and readiness across employee groups. | `silver.employee_profile`, `silver.skill_taxonomy`, `gold.workforce_skill_profile`, `gold.capacity_readiness_daily` |
| Product Portfolio Usage and Adoption Analytics | Adoption, retention, sessionization, feature usage and experimentation across the product portfolio. | `silver.product_event_session`, `gold.product_usage_daily`, `gold.feature_adoption_daily`, `gold.experiment_metrics_daily` |
| Customer Support and Experience Intelligence | SLA, sentiment, support journeys, product defect signals and churn indicators. | `silver.support_case`, `silver.customer_feedback`, `gold.support_sla_daily`, `gold.customer_sentiment_daily` |
| ML/AI Feature and Model Governance | Reproducible training features, model lineage, feature freshness, drift and AI usage audit. | `gold.ml_feature_snapshot`, `feature.enterprise_customer_features`, `gold.model_performance_daily`, `gold.ai_usage_audit_daily` |

## P2 Use Cases

| Use case | Business outcome | First data products |
|---|---|---|
| Marketing Attribution and Growth Intelligence | Campaign-to-revenue, CAC, LTV, consent-aware funnel quality and segment conversion. | `silver.campaign_touch`, `silver.web_lead_event`, `gold.attribution_daily`, `gold.cac_ltv_daily` |
| Procurement, Vendor and Spend Analytics | Spend visibility, vendor risk, contract compliance and savings opportunities. | `silver.vendor_master`, `silver.purchase_order`, `silver.invoice`, `gold.spend_analytics_daily` |
| Privacy, Retention and Regulatory Evidence Hub | DSAR, consent, retention, residency and audit evidence across the data estate. | `gold.privacy_subject_request_status`, `gold.retention_policy_compliance`, `gold.residency_evidence_daily` |
| Enterprise Knowledge and Content Intelligence | Search, recommendation, knowledge-base gaps and content quality across internal and external products. | `silver.knowledge_item`, `gold.content_quality_daily`, `gold.search_gap_daily` |

## Dependency Rule

Do not scale domain analytics before the foundation can prove identity, contracts, quality, lineage,
access and release governance. The first five P0 use cases are intentionally platform-heavy because
they make every later business use case cheaper and safer.

## Product Onboarding Implication

The roadmap now has planned product onboarding packs for:

- `identity-platform`
- `crm-sales`
- `billing-platform`
- `support-platform`
- `hris-workforce`
- `enterprise-commerce`
- `lms-courseflow`

Future products should enter through `enterprise-dp product-scaffold` or an equivalent reviewed
onboarding pack before their data appears in a use-case registry.
