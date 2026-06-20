# 0072 - Payment Fraud Service Package

Date: 2026-06-17
Owner: AI Platform Council

## Participants

- PO/BA Agent
- SA AI Platform Agent
- SA AI Engineer Agent
- Governance Reviewer
- Admin/Ops Reviewer

## Decision

Create `services/payment-fraud-service` as the AI Platform service boundary for
bounded finance payment fraud scoring and entity-link risk evidence.

This promotes `finance-payment-fraud-baseline-v1` from runtime library to a
service-integrated baseline for the non-LMS Billing/Finance use case while
keeping trained anomaly detectors, chargeback backtests and false-positive
monitoring as separate promotion work.

## Accepted Scope

- Serve payment fraud scoring through `POST /v1/payment-fraud/score`.
- Enforce product, use-case and tenant grants from
  `platform/governance/policies/payment-fraud-access-policy.yaml`.
- Accept only pseudonymous account, counterparty and device hashes.
- Reject direct account, counterparty, device, email, phone and payer identity
  fields.
- Set `requiresHumanReview=true` for medium and high risk payment decisions.
- Keep automated adverse payment or account action forbidden.
- Expose health and tenant-safe score, error, direct-identifier rejection,
  entity-link and HITL metrics.

## Deliberate Non-Scope

- Trained anomaly detector, graph model and calibrated classifier artifacts are
  not promoted yet.
- Governed payment and chargeback production snapshots are not bound yet.
- Automated payment hold or account restriction remains forbidden.

## Evidence

- Service package: `services/payment-fraud-service/service.yaml`
- Platform runtime: `platform/src/courseflow_ai_platform/payment_fraud_service.py`
- Access policy: `platform/governance/policies/payment-fraud-access-policy.yaml`
- Service tests: `services/payment-fraud-service/tests/test_service_contract.py`
- Platform tests: `platform/tests/test_payment_fraud_service.py`
- Quality gate: `platform/evaluation/reports/finance-payment-fraud-v1-eval.yaml`

## Acceptance Criteria

- Anomaly/fraud module moves from runtime library to service-integrated baseline.
- Billing/Finance use case calls the shared platform service rather than model
  code directly.
- Direct payment/account/counterparty/device identifiers are rejected at the
  service boundary.
- Medium/high risk scores require human review before any payment or account
  action.
