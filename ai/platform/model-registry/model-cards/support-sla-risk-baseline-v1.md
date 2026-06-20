# support-sla-risk-baseline-v1

## Summary

Deterministic classical/tabular baseline for `support-sla-risk`. The model
scores support cases for SLA breach risk, emits reason codes and requires human
review before any escalation workflow.

## Scope

| Field | Value |
| --- | --- |
| Product | `support-platform` |
| Use case | `support-sla-risk` |
| Model family | `classical_ml`, `classification`, `deterministic_baseline` |
| Runtime status | `runtime_library` |
| Evaluation gate | `support-sla-risk-golden` |

## Inputs

The model consumes bounded support case lifecycle features from
`contracts/features/support-case-features.v1.yaml` and model IO contract
`contracts/models/support-sla-risk-model-io.v1.yaml`.

Key signals:

- priority and lifecycle status
- minutes until SLA due
- case age
- public/internal activity counts
- team capacity flag
- customer tier and reopen count

## Outputs

- `risk_score`
- `risk_band`
- reason codes
- recommended actions
- `requires_human_review`

## Guardrails

- Tenant identifier must be bounded.
- Raw customer identifiers are not accepted.
- Escalation remains advisory and human-reviewed.
- This baseline is deterministic and explainable, not a trained classifier.

## Known Limitations

- No governed support case snapshot binding yet.
- No trained gradient-boosted or neural comparison artifact yet.
- No supervisor feedback loop or false-positive monitoring yet.
- Not hosted as a service.

## Required Next Steps

1. Bind to governed support case snapshots.
2. Compare against a trained tabular classifier.
3. Add shadow supervisor feedback metrics before workflow activation.
