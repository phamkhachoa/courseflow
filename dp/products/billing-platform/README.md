# Billing Platform Product Onboarding

Pilot onboarding pack for billing, subscription, invoice, payment and revenue-recognition facts.

The first runnable slice publishes `finance.billing_transaction.settled.v1` into
`bronze.events_billing_transaction_settled`, `silver.finance_billing_transactions` and
`gold.finance_revenue_daily`. This makes Billing Platform the finance source-of-truth contributor
for certified daily revenue metrics; benefit reconciliation remains a separate finance control
surface for incentives, loyalty, rewards, refunds and exception gaps.
