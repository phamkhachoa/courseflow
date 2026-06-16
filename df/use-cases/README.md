# Enterprise Data Use Cases

`use-cases/` is the group-wide portfolio of business data use cases. It is intentionally outside
`products/` because one enterprise use case can combine signals from many products.

The registry connects PO/BA demand to platform implementation:

- Enterprise domain and priority.
- Business outcome and primary consumers.
- Source products and source systems.
- Planned or existing data products.
- KPI/output expectations.
- Governance, access personas and release gates.
- Optional `pipelineRunners` that link a use case to implemented pipeline runner ids.
- Optional `implementation.pipelines[]` metadata for runnable use cases. Each implementation declares
  the runner id, input topics, input data products, output data products, primary output, quality
  profile and release-evidence profile.

`data-product-control-tower` is a P0 operating use case for the foundation itself. It has Gold output
contracts, a blocking report CLI and a local materialization runner that produces the four Gold
dashboard datasets from `data_product_control_tower_report.v1`.

`identity-access-governance` is the P0 subject and access-risk foundation. It proves that a non-LMS
security product can publish governed identity facts into Bronze, produce `silver.identity_subject`
and publish `gold.access_risk_daily` with access, retention, lineage and release gates.

`customer-account-health` is the P0 Customer 360 foundation. It proves that CRM Sales can publish
tokenized customer account facts into Bronze, produce `silver.customer_identity_link` and publish
`gold.customer_360_profile` for customer success, BI and ML consumers with access, retention,
lineage and release gates.

`enterprise-revenue-intelligence` is the P0 certified revenue foundation. It proves that Billing
Platform can publish governed billing transaction facts into Bronze, produce
`silver.finance_billing_transactions` and publish `gold.finance_revenue_daily` for FP&A,
accounting, revenue operations, compliance and executive semantic metrics.

`enterprise-kpi-scorecard` is the P0 executive reporting foundation. It consumes governed semantic
metric snapshots over certified Gold products and materializes non-PII `gold.enterprise_kpi_daily`
and `gold.executive_scorecard_daily` outputs for leadership, strategy, finance and product
operating reviews.

`customer-support-experience-intelligence` is the P1 Support Experience foundation. It proves that a
support product can publish metadata-only case facts into Bronze, produce `silver.support_case` and
publish `gold.support_sla_daily` for SLA management, service journey intelligence, Customer 360
signals, BI, compliance and ML consumers with governed access and release gates.

Use `enterprise-df portfolio-readiness-report` when PO/BA, SA and product owners need the
group-level decision board: which P0 use cases are blocked, which source products are still draft,
which first-slice contracts are planned, and which source-registry bridges are not production-ready.
It complements Control Tower: portfolio readiness looks at demand/onboarding before delivery, while
Control Tower looks at data product evidence after contracts and pipelines exist.

When an approved source activation exists, pass `--source-activation-ledger
governance/source-activations.yaml`. The report then shows both static source gaps and effective
source gaps, so PO/BA can see which blockers are cleared by current evidence and which still require
source onboarding work.

The registry is validated in CI by `enterprise_df.usecases`.
