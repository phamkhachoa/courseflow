# Data Domains

`domains/` is the enterprise Data Mesh ownership layer. Each domain documents cross-product business
semantics, domain-specific transformations, serving contracts and BA/PO use cases. CourseFlow LMS is
the first onboarded product, but the registry is group-wide and must support future products across
commercial, finance, workforce, risk, compliance, analytics, ML/AI and executive reporting use cases.

Shared infrastructure stays under `platform/`. Versioned contracts that need CI enforcement stay in
`contracts/`.

## Registry

`registry.yaml` is the lightweight machine-readable index for domain ownership and onboarding
planning. Domain READMEs are the human-readable BA/PO and architecture working documents.

Each domain should describe:

- Business capability and decision scope.
- First data products that can become governed Gold, semantic or feature assets.
- First consumers and access personas.
- CourseFlow LMS contribution, if any.
- Other products or source systems that can onboard later.

## Current Domains

| Domain | Business capability | First CourseFlow LMS contribution |
|---|---|---|
| `customer` | Customer, learner, organization and account lifecycle intelligence. | Learner, organization, engagement, review and notification signals. |
| `finance` | Revenue, payment, discount, incentive, loyalty and reconciliation analytics. | Enrollment, paid course, coupon, promotion, loyalty and reward events. |
| `workforce` | Skills, training compliance, readiness and workforce learning intelligence. | Completion, gradebook, certificate and course taxonomy events. |
| `risk-compliance` | Fraud, abuse, anomaly, case queue and operational risk controls. | Quiz/grade anomalies, certificate signals, coupon and loyalty abuse indicators. |
| `product-analytics` | Funnel, cohort, retention, feature usage, experimentation and product health. | Web/mobile/admin clickstream, enrollment funnel and learning runtime events. |
| `ml-ai` | Feature store, model governance, AI usage, next-best-action and scoring datasets. | Recommendation tracking, learner activity and course graph features. |
| `compliance` | Audit evidence, privacy, retention, consent, residency and access governance. | Access-control, entitlement, learner PII and tenant/org scope evidence. |
| `enterprise-reporting` | KPI catalog, semantic metrics and executive reporting across domains. | Learner success, course quality and organization learning dashboards. |
| `recommendation` | Recommendation signals, ML training datasets and reverse ETL. | Related-course impression, click and enrollment signals. |
