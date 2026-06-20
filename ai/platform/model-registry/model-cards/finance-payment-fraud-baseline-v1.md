# finance-payment-fraud-baseline-v1

## Summary

Deterministic anomaly/fraud risk baseline for `finance-payment-fraud-scoring`.
The model scores payment events, emits explainable reason codes and returns
entity-link evidence for analyst review.

## Scope

| Field | Value |
| --- | --- |
| Product | `billing-finance` |
| Use case | `finance-payment-fraud-scoring` |
| Model family | `classical_ml`, `anomaly_detection`, `graph_ml`, `deterministic_baseline` |
| Runtime status | `runtime_library` |
| Evaluation gate | `finance-payment-fraud-golden` |

## Inputs

The model consumes bounded payment, account and chargeback features from
`contracts/features/finance-payment-risk-features.v1.yaml` and model IO contract
`contracts/models/finance-payment-fraud-model-io.v1.yaml`.

Key signals:

- payment amount, method, country and currency
- 1-hour and 24-hour payment velocity
- failed attempts and chargeback history
- account age and payment method verification
- linked account and shared counterparty graph counts
- prior manual risk review outcome

## Outputs

- `risk_score`
- `risk_band`
- reason codes
- entity-link evidence
- recommended analyst actions
- `requires_human_review`
- `automated_adverse_action_allowed=false`

## Guardrails

- Tenant identifier must be bounded.
- Account, counterparty and device identifiers must be pseudonymous hashes.
- The model cannot approve automated payment holds or account actions.
- Medium and high risk payments require human review.
- This baseline is deterministic and explainable, not a trained fraud model.

## Known Limitations

- No governed payment snapshot binding yet.
- No chargeback-label backtest or false-positive calibration yet.
- No trained isolation forest, gradient boosted or graph neural comparison yet.
- Not hosted as a service.

## Required Next Steps

1. Bind to governed payment and chargeback outcome snapshots.
2. Compare against a trained anomaly detector and calibrated classifier.
3. Add shadow false-positive and analyst-overturn monitoring.
