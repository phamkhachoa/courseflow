# 0032 - Finance Payment Fraud Baseline

Date: 2026-06-17

## Participants

- PO/BA: Finance product owner
- SA AI Platform: Platform architecture and governance owner
- SA AI Engineer: Runtime baseline and evaluation owner

## Decision

Promote `finance-payment-fraud-scoring` from a roadmap-only finance risk use
case to a runtime-library baseline backed by model IO, golden evaluation, model
card and artifact manifest evidence.

## Shipped Artifacts

- Runtime library:
  `models/anomaly_fraud/payment_fraud_baseline/payment_fraud_baseline.py`
- Unit tests:
  `models/anomaly_fraud/payment_fraud_baseline/tests/test_payment_fraud_baseline.py`
- Model IO contract:
  `contracts/models/finance-payment-fraud-model-io.v1.yaml`
- Golden evaluation:
  `platform/evaluation/datasets/finance-payment-fraud-golden.yaml`
- Evaluation report:
  `platform/evaluation/reports/finance-payment-fraud-v1-eval.yaml`
- Model card:
  `platform/model-registry/model-cards/finance-payment-fraud-baseline-v1.md`
- Artifact manifest:
  `platform/artifacts/manifests/finance-payment-fraud-baseline-v1.yaml`

## Platform Impact

- `anomaly-fraud-risk` moves from `registered_roadmap` to `executable_gate`.
- `graph-knowledge-intelligence` moves from `registered_roadmap` to
  `executable_gate` because the baseline emits entity-link evidence.
- `finance-payment-fraud-scoring-discovery` no longer needs platform-build
  work before solution design.
- The AI platform now has one more non-LMS runtime library in finance/risk.

## Guardrails

- Raw account, counterparty and device identifiers are rejected.
- Medium and high risk payments require human review.
- Automated adverse action is not allowed.
- Payment hold or account action remains outside the model and requires human
  approval under the governance policy.

## Required Next Steps

1. Bind the baseline to governed payment and chargeback snapshots.
2. Compare against a trained anomaly detector and calibrated classifier.
3. Add shadow false-positive and analyst-overturn monitoring before workflow
   activation.
