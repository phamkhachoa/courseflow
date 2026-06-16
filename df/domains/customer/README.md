# Customer Data Domain

This domain owns customer, learner, organization and account lifecycle intelligence across
enterprise products. It provides governed identity, engagement, health and retention data products
without replacing product-owned OLTP systems.

## Business Capability

Customer creates a conformed understanding of people, organizations, account relationships,
engagement, lifecycle stage, retention risk and customer health across products.

## First Data Products

| Data product | Purpose | First source or contribution |
|---|---|---|
| `silver.customer_identity_link` | Links product-local customer, account, organization and external identifiers. | CRM Sales account and tokenized customer identifiers. |
| `silver.support_case` | Conformed support case state for service journey and operational support analysis. | Support Platform case metadata and tokenized customer identifiers. |
| `gold.customer_360_profile` | Business-ready customer and organization profile with lifecycle, health and engagement attributes. | CRM Sales lifecycle, consent, revenue signal, product usage and support-case rollups. |
| `gold.support_sla_daily` | Daily support SLA, breach, escalation, reopen and satisfaction facts. | Support Platform service events grouped by product, organization, account, customer, channel and priority. |
| `gold.customer_engagement_daily` | Daily engagement facts for retention, success and growth analysis. | Course views, enrollments, reviews, completions and notification interactions. |

## First Consumers

- Customer success teams tracking account health and learner engagement.
- Growth analytics teams measuring retention and lifecycle movement.
- Enterprise reporting for customer and organization KPIs.
- ML/AI domain for churn, next-best-action and personalization features.

## First Runnable Slice

CRM Sales contributes `customer.account.changed.v1` events into
`bronze.events_customer_account_changed`, `silver.customer_identity_link` and
`gold.customer_360_profile`. This is the first runnable Customer 360 slice and keeps direct
identifiers out of Bronze/Silver/Gold by using tokenized subject keys.

Support Platform contributes `customer.support_case.changed.v1` events into
`bronze.events_support_case_changed`, `silver.support_case` and `gold.support_sla_daily`. This is the
first runnable Customer Experience slice and intentionally captures metadata-only support facts,
not ticket transcripts, message bodies, attachments or direct contact identifiers.

## CourseFlow LMS Contribution

CourseFlow LMS contributes learner profiles, organization membership, tenant scope, course activity,
reviews, notifications and engagement outcomes. It is the first source for learning-related customer
health and education engagement signals.

## Future Product Onboarding

- CRM and sales operations for account hierarchy, opportunities and customer lifecycle stage.
- Commerce and billing for purchase history and monetization status.
- Support platforms for tickets, satisfaction and service interactions.
- Marketing automation for campaign touchpoints and consented engagement.

## Domain-Specific Rules

- Product-local identifiers must be preserved for lineage but exposed through conformed surrogate
  keys for cross-product use.
- PII attributes require classification, masking and access personas before self-service exposure.
- Customer health scores must publish input features, calculation date and source coverage.
- Cross-tenant customer views must enforce row-level isolation and organization scope.
