# Finance Data Domain

This domain owns revenue, payment, discount, incentive, loyalty, reconciliation and margin analytics
across enterprise products. It supports finance-grade data products for FP&A, accounting, revenue
operations and executive reporting.

## Business Capability

Finance provides governed facts for revenue recognition support, payment status, discount usage,
benefit reconciliation, incentive cost, loyalty liability, unit economics and financial controls.

## First Data Products

| Data product | Purpose | First source or contribution |
|---|---|---|
| `silver.finance_billing_transactions` | Normalized billing transaction facts for revenue intelligence and finance drill-through. | Billing Platform settlement, invoice and revenue recognition events. |
| `gold.finance_revenue_daily` | Daily revenue, gross booking and net revenue facts by product, tenant, product line and currency. | Billing Platform settlement events, with CourseFlow and Support Platform as source products. |
| `gold.finance_benefit_reconciliation` | Reconciles paid orders, discounts, loyalty points, rewards and refunds. | Enterprise Commerce settlement events, with CourseFlow as the first source product. |
| `gold.finance_margin_daily` | Product-level unit economics and contribution margin inputs. | CourseFlow course price, discount, enrollment and partner payout inputs. |

## First Consumers

- FP&A for revenue, margin and forecast reporting.
- Accounting for reconciliation evidence and period-close support.
- Revenue operations for discount and promotion governance.
- Enterprise reporting for executive financial KPIs.

## CourseFlow LMS Contribution

CourseFlow LMS contributes enrollments, paid course transactions, coupons, promotions, loyalty
rewards, refund indicators if available, and course or organization dimensions for revenue slicing.
Enterprise Commerce contributes the first runnable finance settlement stream:
`finance.benefit_settled.v1`.

## Billing Platform Contribution

Billing Platform contributes `finance.billing_transaction.settled.v1` events into
`bronze.events_billing_transaction_settled`, `silver.finance_billing_transactions` and
`gold.finance_revenue_daily`. This is the first runnable certified revenue slice. It keeps customer
subject hashes in Silver for governed finance support workflows, while Gold daily revenue aggregates
remove customer and account identifiers for executive and BI serving.

## Future Product Onboarding

- Payment platform for settlement, refund, chargeback and payment method data.
- Subscription billing for recurring revenue, invoices and contract lifecycle.
- Marketplace products for seller payouts, commissions and fee models.
- ERP or accounting systems for general ledger, cost center and period-close data.

## Domain-Specific Rules

- Finance Gold products must retain source transaction id, product code, accounting period and
  reconciliation status.
- Monetary facts require currency, exchange-rate basis and decimal-safe storage.
- Discounts, loyalty and incentives must be separable from gross revenue.
- Finance-facing data products require stronger completeness and reconciliation SLOs than exploratory
  product analytics datasets.
