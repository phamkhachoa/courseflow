# Risk and Compliance Controls Data Domain

This domain owns fraud, abuse, anomaly, control exception and operational risk data products. It is
separate from the Compliance domain, which owns audit, privacy, retention and regulatory evidence.

## Business Capability

Risk and Compliance Controls detects and prioritizes business risk signals, operational control
failures, fraud patterns, abuse indicators and investigation queues across products.

## First Data Products

| Data product | Purpose | First source or contribution |
|---|---|---|
| `gold.risk_signal_daily` | Daily risk signal facts by product, tenant, person, organization and risk category. | CourseFlow quiz, grade, certificate, coupon and loyalty anomalies. |
| `gold.fraud_case_queue` | Prioritized investigation queue with evidence, severity and recommended action. | CourseFlow certificate fraud, account abuse and benefit abuse indicators. |
| `gold.control_exception_daily` | Control failures, threshold breaches and unresolved exception metrics. | CourseFlow grade override, entitlement and promotion control signals. |

## First Consumers

- Risk operations for triage and investigation.
- Trust and safety for abuse detection and response.
- Finance controls for discount, coupon, reward and payment anomalies.
- Compliance teams for control evidence and exception escalation.

## CourseFlow LMS Contribution

CourseFlow LMS contributes quiz and grade anomalies, certificate issuance signals, account behavior,
entitlement checks, coupon use, loyalty rewards and promotion abuse indicators.

## Future Product Onboarding

- Payments for chargeback, refund and settlement risk.
- Identity systems for login, device, session and account takeover signals.
- Commerce products for order abuse, seller risk and promotion abuse.
- Customer support for investigation notes, disputes and escalation outcomes.

## Domain-Specific Rules

- Risk scores must publish model or rule version, severity, evidence links and decision timestamp.
- Case queues must preserve source event ids and investigation outcome lineage.
- Sensitive risk indicators require restricted access and audit logging.
- Automated actions must be traceable to an approved rule, model or human decision.
