# Model Card: Operations Routing Policy Simulator V1

## Identity

| Field | Value |
|---|---|
| Model ID | `operations-routing-policy-simulator-v1` |
| Algorithm | deterministic constrained routing policy simulator |
| Use case | `operations-routing-optimization` |
| Product | `enterprise-operations` |
| Owner | `ai-platform` |
| Status | runtime library baseline |

## Intended Use

Evaluate constrained routing decisions offline before any contextual bandit or
RL policy is promoted to shadow or online activation.

## Not Intended For

- Fully automated adverse routing decisions.
- Online exploration without explicit safe-exploration budget.
- Replacing supervisor review for high-impact escalations.
- Learning from live traffic without governed logged-policy datasets.

## Inputs

| Input | Description |
|---|---|
| tenant ID | Tenant boundary |
| policy ID | Candidate policy identifier |
| safe exploration budget | Maximum allowed exploration share |
| work item context | Priority, work type, required skills and expected effort |
| queue states | Capacity, backlog, handle time and skill coverage |
| baseline queue ID | Existing or fallback assignment for lift comparison |

## Outputs

| Output | Description |
|---|---|
| assigned queue | Recommended queue ID |
| policy score | Bounded deterministic policy score |
| expected SLA success | Proxy outcome score for offline comparison |
| baseline score delta | Difference from baseline queue score |
| exploration budget used | Offline safe-exploration amount |
| constraint violations | Missing skill or capacity constraints |
| reason codes | Transparent policy reasons |
| human-review flag | Required when constraints are violated |

## Runtime Method

The simulator scores each queue using skill match, available capacity, backlog
pressure and expected effort fit. It compares the selected queue against a
baseline queue, blocks unsafe exploration for high-priority work and emits
human-review flags when constraints are violated.

This is a simulator/offline policy baseline. It proves the policy IO,
evaluation and governance path for RL/bandit decisioning, but it is not an
online learner or production routing service.

## Governance

- Tenant ID is required.
- Safe exploration budget is bounded.
- High-priority work does not use exploration.
- Constraint violations require human review.
- Online activation requires shadow policy review and governed logged-policy
  datasets.

## Known Limitations

- Hand-authored scoring only.
- No counterfactual estimator yet.
- No live queue feedback loop.
- No online exploration service.

## Monitoring

Track assignment override rate, SLA lift, transfer count, exploration budget
usage, constraint violations, supervisor review outcomes and policy age before
shadow or active promotion.
