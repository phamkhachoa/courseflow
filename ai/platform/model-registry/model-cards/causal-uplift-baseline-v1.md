# Model Card: Causal Uplift Baseline V1

## Identity

| Field | Value |
|---|---|
| Model ID | `causal-uplift-baseline-v1` |
| Algorithm | deterministic two-proportion uplift gate |
| Use case | `enterprise-experimentation-uplift` |
| Product | `ai-platform` |
| Owner | `ai-platform` |
| Status | runtime library baseline |

## Intended Use

Estimate treatment-vs-control lift from governed experiment snapshots, flag
statistical confidence, enforce guardrail regression stops and route high-impact
interventions to human review.

## Not Intended For

- Observational causal inference without assignment evidence.
- Automatic rollout or rollback decisions.
- Multi-arm bandit optimization.
- Medical, financial or employment-impacting decisions without domain review.

## Inputs

| Input | Description |
|---|---|
| tenant and experiment IDs | Tenant and experiment boundary |
| outcome name | Business metric under review |
| treatment/control names | Compared intervention labels |
| treatment/control counts | Observed arm sizes |
| treatment/control successes | Outcome successes by arm |
| minimum detectable lift | Business threshold for meaningful lift |
| confidence level | Statistical gate threshold |
| guardrail delta | Safety or quality guardrail movement |
| high-impact flag | Forces human review for learner/customer-impacting changes |
| segment count | Flags multiplicity review when many segments are inspected |

## Outputs

| Output | Description |
|---|---|
| treatment/control rates | Observed success rates |
| absolute/relative lift | Treatment lift versus control |
| z-score and confidence score | Deterministic two-proportion confidence signal |
| decision band | Positive, negative, directional, inconclusive or guardrail risk |
| recommendation | Continue, stop/redesign or promote to shadow review |
| reason codes | Explainable review reasons |
| human-review flag | Required for high-impact or risky decisions |

## Runtime Method

The baseline computes a pooled two-proportion z-score from aggregate treatment
and control outcomes. It compares observed lift with the configured minimum
detectable lift, applies a confidence threshold and stops experiments when
guardrail metrics regress.

This is a deterministic runtime library. It proves a reusable causal review
contract for LMS interventions, enterprise personalization and operations
policy experiments before a full experimentation service is introduced.

## Governance

- Tenant ID is required.
- High-impact interventions require human review.
- Guardrail regression produces a stop/redesign recommendation.
- Online activation requires shadow review and assignment snapshot evidence.

## Known Limitations

- No covariate adjustment.
- No sample-ratio mismatch check yet.
- No multi-arm or sequential testing correction.
- No observational causal inference.

## Monitoring

Track assignment snapshot freshness, arm balance, guardrail regression rate,
human override rate, segment multiplicity, promoted experiment outcomes and
post-rollout metric drift.
