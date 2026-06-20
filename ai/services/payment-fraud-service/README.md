# Payment Fraud Service

Policy-enforced runtime service for `finance-payment-fraud-baseline-v1`.

The service promotes the payment fraud/anomaly runtime library into a reusable
AI Platform service boundary for Billing/Finance payment risk scoring.

## Routes

| Method | Path | Scope |
|---|---|---|
| `POST` | `/v1/payment-fraud/score` | `internal:ai-platform:payment-fraud:score` |
| `GET` | `/v1/payment-fraud/health` | `internal:ai-platform:payment-fraud:ops` |
| `GET` | `/v1/payment-fraud/metrics` | `internal:ai-platform:payment-fraud:ops` |

## Guardrails

- Product, use-case and tenant grants come from
  `platform/governance/policies/payment-fraud-access-policy.yaml`.
- Requests must use pseudonymous account, counterparty and device hashes.
- Direct account, counterparty, device, email, phone or payer identifiers are
  rejected at the service boundary.
- Medium and high risk outputs require human review before payment hold or
  account action.
- Automated adverse payment or account action remains forbidden.

## Local Commands

```bash
PYTHONPATH=src:../../platform/src python3.11 -m pytest
PYTHONPATH=src:../../platform/src python3.11 -m ruff check .
PYTHONPATH=src:../../platform/src python3.11 -m courseflow_payment_fraud_service manifest
```
