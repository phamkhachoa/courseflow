# Payment Fraud Baseline

Deterministic anomaly/fraud risk baseline for `finance-payment-fraud-scoring`.
It consumes bounded payment, account and chargeback features, then emits a
human-reviewable risk score, reason codes and entity-link evidence.

This model is deliberately advisory. It never permits automated adverse action;
high-risk payments are routed to a human review queue before any payment hold or
account action.

## Runtime Entry Point

```text
PaymentFraudRiskBaseline.predict(payload)
```

## Evidence

- Feature contract: `contracts/features/finance-payment-risk-features.v1.yaml`
- Model IO contract: `contracts/models/finance-payment-fraud-model-io.v1.yaml`
- Golden eval: `platform/evaluation/datasets/finance-payment-fraud-golden.yaml`
- Model card: `platform/model-registry/model-cards/finance-payment-fraud-baseline-v1.md`
- Manifest: `platform/artifacts/manifests/finance-payment-fraud-baseline-v1.yaml`
